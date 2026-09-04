// Replay capture.bin — no Metal. Replays AGX IOKit calls and trap submits.

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <IOKit/IOKitLib.h>

#define CAP_MAGIC 0x43584741
#define CAP_VERSION 2
#define MAX_ADDR_MAP 8192
#define MAX_SCALARS 16
#define MAX_STRUCT 0x500
#define MAX_TRAP_SNAP 0x1000
#define MAX_RETAINED 512
#define MAX_CAPTURE_REGION (64ull * 1024ull * 1024ull)

enum cap_type {
	CAP_OPEN = 1,
	CAP_CALL = 2,
	CAP_TRAP = 3,
	CAP_MEMORY = 4,
};

enum cap_memory_kind {
	CAP_MEMORY_RESOURCE = 1,
	CAP_MEMORY_TRAP_AUX = 2,
	CAP_MEMORY_EXPECTED = 3,
};

struct cap_hdr {
	uint32_t magic, version, count, _pad;
};

struct cap_open {
	uint8_t type;
	uint8_t _pad[3];
	uint32_t client_type;
	int32_t rc;
	uint32_t conn;
};

struct cap_call_hdr {
	uint8_t type;
	uint8_t _pad[3];
	uint32_t conn;
	uint32_t selector;
	uint32_t scalar_in_cnt;
	uint32_t struct_in_sz;
};

struct cap_call_tail {
	int32_t rc;
	uint32_t scalar_out_cnt;
	uint32_t struct_out_sz;
};

struct cap_trap_hdr {
	uint8_t type;
	uint8_t _pad[3];
	uint32_t conn;
	uint32_t trap_idx;
	uint64_t p1, p2, p3, p4;
	uint32_t snap_sz;
};

struct cap_trap_tail {
	int32_t rc;
};

struct cap_memory_hdr {
	uint8_t type;
	uint8_t kind;
	uint16_t flags;
	uint32_t _pad;
	uint64_t address;
	uint64_t size;
};

struct addr_map { uint64_t old_val, new_val, size; };
static struct addr_map maps[MAX_ADDR_MAP];
static unsigned nmaps;
static void *retained[MAX_RETAINED];
static unsigned nretained;

static int read_exact(FILE *fp, void *buf, size_t size)
{
	return size == 0 || fread(buf, 1, size, fp) == size;
}

static void add_range(uint64_t old_v, uint64_t new_v, uint64_t size)
{
	if (!old_v || !new_v)
		return;
	for (unsigned i = 0; i < nmaps; i++) {
		if (maps[i].old_val == old_v && maps[i].size == size) {
			maps[i].new_val = new_v;
			return;
		}
	}
	if (nmaps < MAX_ADDR_MAP)
		maps[nmaps++] = (struct addr_map){ old_v, new_v, size };
}

static void add_map(uint64_t old_v, uint64_t new_v)
{
	add_range(old_v, new_v, 0);
}

static uint64_t remap(uint64_t v)
{
	for (unsigned i = 0; i < nmaps; i++)
		if (!maps[i].size && maps[i].old_val == v)
			return maps[i].new_val;
	for (unsigned i = 0; i < nmaps; i++)
		if (maps[i].size && maps[i].old_val <= v &&
			v < maps[i].old_val + maps[i].size)
			return maps[i].new_val + (v - maps[i].old_val);
	return v;
}

static int has_mapping(uint64_t v)
{
	for (unsigned i = 0; i < nmaps; i++) {
		if (maps[i].old_val == v)
			return 1;
		if (maps[i].size && maps[i].old_val <= v &&
			v < maps[i].old_val + maps[i].size)
			return 1;
	}
	return 0;
}

static void patch_u64_buf(void *buf, size_t sz)
{
	for (size_t i = 0; i + 8 <= sz; i += 4) {
		uint64_t old_v, new_v;
		memcpy(&old_v, (uint8_t *)buf + i, sizeof(old_v));
		new_v = remap(old_v);
		if (new_v != old_v)
			memcpy((uint8_t *)buf + i, &new_v, sizeof(new_v));
	}
}

static io_service_t find_agx_service(void)
{
	const char *names[] = {
		"AGXAcceleratorG13G_B0", "AGXAcceleratorG13G",
		"AGXAcceleratorG14G", "AGXAcceleratorG15G",
		"AGXAcceleratorG16G", "AGXAcceleratorG17G", NULL,
	};
	for (int i = 0; names[i]; i++) {
		io_service_t svc = IOServiceGetMatchingService(kIOMainPortDefault,
			IOServiceNameMatching(names[i]));
		if (svc)
			return svc;
	}
	io_iterator_t it = 0;
	IOServiceGetMatchingServices(kIOMainPortDefault,
		IOServiceMatching("AGXAccelerator"), &it);
	io_service_t svc = IOIteratorNext(it);
	IOObjectRelease(it);
	return svc;
}

static void learn_call_maps(uint32_t selector,
		const uint8_t *cap, size_t cap_sz,
		const uint8_t *live, size_t live_sz)
{
	uint64_t old_v = 0, new_v = 0, size = 0;
	if (selector == 0x09 && cap_sz >= 0x30 && live_sz >= 0x30) {
		memcpy(&old_v, cap + 8, sizeof(old_v));
		memcpy(&new_v, live + 8, sizeof(new_v));
		memcpy(&size, cap + 0x28, sizeof(size));
		add_range(old_v, new_v, size);
		memcpy(&old_v, cap + 16, sizeof(old_v));
		memcpy(&new_v, live + 16, sizeof(new_v));
		add_map(old_v, new_v);
	} else if ((selector == 0x0e || selector == 0x10) &&
		cap_sz >= 16 && live_sz >= 16) {
		memcpy(&old_v, cap, sizeof(old_v));
		memcpy(&new_v, live, sizeof(new_v));
		if (selector == 0x0e) {
			uint32_t size32 = 0;
			memcpy(&size32, cap + 8, sizeof(size32));
			size = size32;
		} else {
			size = 0x4000;
		}
		add_range(old_v, new_v, size);
	}
}

static int replay_call(io_connect_t conn, FILE *fp, int idx)
{
	struct cap_call_hdr hdr;
	if (!read_exact(fp, &hdr, sizeof(hdr)) ||
		hdr.scalar_in_cnt > MAX_SCALARS || hdr.struct_in_sz > MAX_STRUCT)
		return -1;

	uint64_t scal_in[MAX_SCALARS] = {0};
	uint8_t struct_in[MAX_STRUCT] = {0};
	if (!read_exact(fp, scal_in,
			hdr.scalar_in_cnt * sizeof(uint64_t)) ||
		!read_exact(fp, struct_in, hdr.struct_in_sz))
		return -1;

	struct cap_call_tail tail;
	if (!read_exact(fp, &tail, sizeof(tail)) ||
		tail.scalar_out_cnt > MAX_SCALARS || tail.struct_out_sz > MAX_STRUCT)
		return -1;

	uint64_t cap_scalars[MAX_SCALARS] = {0};
	uint8_t cap_struct[MAX_STRUCT] = {0};
	if (!read_exact(fp, cap_scalars,
			tail.scalar_out_cnt * sizeof(uint64_t)) ||
		!read_exact(fp, cap_struct, tail.struct_out_sz))
		return -1;

	patch_u64_buf(struct_in, hdr.struct_in_sz);

	uint64_t scal_out[MAX_SCALARS] = {0};
	uint32_t scal_out_cnt = tail.scalar_out_cnt;
	uint8_t live_out[MAX_STRUCT] = {0};
	size_t live_out_sz = tail.struct_out_sz;

	kern_return_t rc = IOConnectCallMethod(conn, hdr.selector,
		hdr.scalar_in_cnt ? scal_in : NULL, hdr.scalar_in_cnt,
		hdr.struct_in_sz ? struct_in : NULL, hdr.struct_in_sz,
		tail.scalar_out_cnt ? scal_out : NULL,
		tail.scalar_out_cnt ? &scal_out_cnt : NULL,
		live_out_sz ? live_out : NULL,
		live_out_sz ? &live_out_sz : NULL);

	printf("[%d] sel=0x%02x rc=0x%x (expected 0x%x) out_sz=%zu\n",
		idx, hdr.selector, rc, tail.rc, live_out_sz);

	if (rc == KERN_SUCCESS && tail.struct_out_sz)
		learn_call_maps(hdr.selector, cap_struct, tail.struct_out_sz,
			live_out, live_out_sz);

	return rc == tail.rc && scal_out_cnt == tail.scalar_out_cnt &&
		live_out_sz == tail.struct_out_sz ? 0 : 1;
}

static int replay_trap(io_connect_t conn, FILE *fp, int idx)
{
	struct cap_trap_hdr hdr;
	if (!read_exact(fp, &hdr, sizeof(hdr)) || hdr.snap_sz > MAX_TRAP_SNAP)
		return -1;

	uint8_t *snap = calloc(1, hdr.snap_sz ? hdr.snap_sz : 1);
	if (!snap || !read_exact(fp, snap, hdr.snap_sz)) {
		free(snap);
		return -1;
	}

	struct cap_trap_tail tail;
	if (!read_exact(fp, &tail, sizeof(tail))) {
		free(snap);
		return -1;
	}

	void *buf = NULL;
	int keep_buf = 0;
	size_t alloc_sz = hdr.snap_sz ? hdr.snap_sz + 0x100 : 0;
	if (alloc_sz) {
		if (posix_memalign(&buf, 0x10, alloc_sz) != 0) {
			free(snap);
			return -1;
		}
		memset(buf, 0, alloc_sz);
		memcpy(buf, snap, hdr.snap_sz);
		patch_u64_buf(buf, hdr.snap_sz);
		if (nretained < MAX_RETAINED) {
			retained[nretained++] = buf;
			keep_buf = 1;
		}
	}

	uintptr_t p3 = (uintptr_t)buf;
	uint64_t p4_off = hdr.p4 && hdr.p3 ? hdr.p4 - hdr.p3 : 0;
	uintptr_t p4 = p4_off > 0 && p4_off < alloc_sz ? p3 + p4_off : 0;

	kern_return_t rc = IOConnectTrap4(conn, hdr.trap_idx,
		hdr.p1, hdr.p2, p3, p4);

	printf("[%d] trap%u rc=0x%x (expected 0x%x) snap=%u bytes\n",
		idx, hdr.trap_idx, rc, tail.rc, hdr.snap_sz);

	free(snap);
	if (!keep_buf)
		free(buf);
	return rc == tail.rc ? 0 : 1;
}

static int replay_memory(FILE *fp, int idx)
{
	struct cap_memory_hdr hdr;
	if (!read_exact(fp, &hdr, sizeof(hdr)) ||
		hdr.size > MAX_CAPTURE_REGION || hdr.size > SIZE_MAX)
		return -1;

	uint8_t *data = malloc(hdr.size ? (size_t)hdr.size : 1);
	if (!data || !read_exact(fp, data, (size_t)hdr.size)) {
		free(data);
		return -1;
	}

	if (hdr.kind == CAP_MEMORY_TRAP_AUX) {
		void *buf = NULL;
		if (nretained >= MAX_RETAINED ||
			posix_memalign(&buf, 0x10, (size_t)hdr.size + 0x10) != 0) {
			free(data);
			return -1;
		}
		add_range(hdr.address, (uintptr_t)buf, hdr.size);
		patch_u64_buf(data, (size_t)hdr.size);
		memcpy(buf, data, (size_t)hdr.size);
		retained[nretained++] = buf;
		printf("[%d] trap aux 0x%llx -> 0x%llx (%llu bytes)\n", idx,
			(unsigned long long)hdr.address,
			(unsigned long long)(uintptr_t)buf,
			(unsigned long long)hdr.size);
		free(data);
		return 0;
	}

	uint64_t target = remap(hdr.address);
	if (!has_mapping(hdr.address)) {
		fprintf(stderr, "[%d] memory address 0x%llx was not remapped\n",
			idx, (unsigned long long)hdr.address);
		free(data);
		return 1;
	}

	if (hdr.kind == CAP_MEMORY_RESOURCE) {
		patch_u64_buf(data, (size_t)hdr.size);
		memcpy((void *)(uintptr_t)target, data, (size_t)hdr.size);
		printf("[%d] restored 0x%llx bytes 0x%llx -> 0x%llx\n", idx,
			(unsigned long long)hdr.size,
			(unsigned long long)hdr.address,
			(unsigned long long)target);
		free(data);
		return 0;
	}

	if (hdr.kind == CAP_MEMORY_EXPECTED) {
		int matched = 0;
		for (unsigned i = 0; i < 5000; ++i) {
			if (memcmp((const void *)(uintptr_t)target, data,
				(size_t)hdr.size) == 0) {
				matched = 1;
				break;
			}
			usleep(1000);
		}
		printf("[%d] output %s @0x%llx (%llu bytes)\n", idx,
			matched ? "PASS" : "FAIL", (unsigned long long)target,
			(unsigned long long)hdr.size);
		free(data);
		return matched ? 0 : 1;
	}

	fprintf(stderr, "[%d] unknown memory kind %u\n", idx, hdr.kind);
	free(data);
	return 1;
}

int main(int argc, char **argv)
{
	const char *path = argc > 1 ? argv[1] : "add.cap";
	FILE *fp = fopen(path, "rb");
	if (!fp) {
		perror(path);
		return 1;
	}

	struct cap_hdr file_hdr;
	if (fread(&file_hdr, sizeof(file_hdr), 1, fp) != 1 ||
	    file_hdr.magic != CAP_MAGIC || file_hdr.version < 1 ||
	    file_hdr.version > CAP_VERSION) {
		fprintf(stderr, "invalid capture %s\n", path);
		fclose(fp);
		return 1;
	}

	io_service_t svc = find_agx_service();
	if (!svc) {
		fprintf(stderr, "no AGX accelerator\n");
		fclose(fp);
		return 1;
	}

	io_connect_t conn = 0;
	int idx = 0, fails = 0, malformed = 0;

	printf("replaying %s\n", path);

	while (1) {
		uint8_t type;
		if (fread(&type, 1, 1, fp) != 1)
			break;
		if (type == 0)
			break;
		if (fseek(fp, -1, SEEK_CUR) != 0) {
			malformed = 1;
			break;
		}

		if (type == CAP_OPEN) {
			struct cap_open rec;
			if (!read_exact(fp, &rec, sizeof(rec))) {
				malformed = 1;
				break;
			}
			if (!conn) {
				kern_return_t kr = IOServiceOpen(svc, mach_task_self(),
					rec.client_type, &conn);
				printf("[%d] IOServiceOpen type=0x%x conn=0x%x rc=0x%x "
					"(expected 0x%x)\n", idx, rec.client_type, conn,
					kr, rec.rc);
				fails += kr != rec.rc;
				if (kr != KERN_SUCCESS) {
					malformed = 1;
					break;
				}
			}
			idx++;
		} else if (type == CAP_CALL) {
			if (!conn) {
				fprintf(stderr, "call before open\n");
				malformed = 1;
				break;
			}
			int rc = replay_call(conn, fp, idx++);
			if (rc < 0) {
				malformed = 1;
				break;
			}
			fails += rc;
		} else if (type == CAP_TRAP) {
			if (!conn) {
				fprintf(stderr, "trap before open\n");
				malformed = 1;
				break;
			}
			int rc = replay_trap(conn, fp, idx++);
			if (rc < 0) {
				malformed = 1;
				break;
			}
			fails += rc;
		} else if (type == CAP_MEMORY) {
			if (!conn) {
				fprintf(stderr, "memory before open\n");
				malformed = 1;
				break;
			}
			int rc = replay_memory(fp, idx++);
			if (rc < 0) {
				malformed = 1;
				break;
			}
			fails += rc;
		} else {
			fprintf(stderr, "bad type %u at op %d\n", type, idx);
			malformed = 1;
			break;
		}
	}
	if (malformed) {
		fprintf(stderr, "capture ended with an invalid record at op %d\n", idx);
		fails++;
	}

	if (conn)
		IOServiceClose(conn);
	IOObjectRelease(svc);
	fclose(fp);
	for (unsigned i = 0; i < nretained; ++i)
		free(retained[i]);

	printf("done: %d ops, %d failures, %u addr maps\n", idx, fails, nmaps);
	return fails ? 1 : 0;
}
