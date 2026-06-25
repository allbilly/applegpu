// Replay capture.bin — no Metal. Replays AGX IOKit calls and trap submits.

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <IOKit/IOKitLib.h>

#define CAP_MAGIC 0x43584741
#define MAX_ADDR_MAP 8192
#define MAX_STRUCT 0x500

enum cap_type { CAP_OPEN = 1, CAP_CALL = 2, CAP_TRAP = 3 };

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

struct addr_map { uint64_t old_val, new_val; };
static struct addr_map maps[MAX_ADDR_MAP];
static unsigned nmaps;

static void add_map(uint64_t old_v, uint64_t new_v)
{
	if (!old_v || !new_v || old_v == new_v)
		return;
	for (unsigned i = 0; i < nmaps; i++) {
		if (maps[i].old_val == old_v) {
			maps[i].new_val = new_v;
			return;
		}
	}
	if (nmaps < MAX_ADDR_MAP)
		maps[nmaps++] = (struct addr_map){ old_v, new_v };
}

static uint64_t remap(uint64_t v)
{
	for (unsigned i = 0; i < nmaps; i++)
		if (maps[i].old_val == v)
			return maps[i].new_val;
	return v;
}

static void patch_u64_buf(void *buf, size_t sz)
{
	for (size_t i = 0; i + 8 <= sz; i += 8) {
		uint64_t *p = (uint64_t *)((uint8_t *)buf + i);
		*p = remap(*p);
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

static void learn_resource_maps(const uint8_t *cap, size_t cap_sz,
		const uint8_t *live, size_t live_sz)
{
	if (cap_sz < 24 || live_sz < 24)
		return;
	add_map(*(const uint64_t *)(cap + 8), *(const uint64_t *)(live + 8));
	add_map(*(const uint64_t *)(cap + 16), *(const uint64_t *)(live + 16));
}

static int replay_call(io_connect_t conn, FILE *fp, int idx)
{
	struct cap_call_hdr hdr;
	if (fread(&hdr, sizeof(hdr), 1, fp) != 1)
		return -1;

	uint64_t *scal_in = NULL;
	uint8_t *struct_in = NULL;

	if (hdr.scalar_in_cnt) {
		scal_in = calloc(hdr.scalar_in_cnt, sizeof(uint64_t));
		fread(scal_in, sizeof(uint64_t), hdr.scalar_in_cnt, fp);
	}
	if (hdr.struct_in_sz) {
		struct_in = calloc(1, hdr.struct_in_sz);
		fread(struct_in, 1, hdr.struct_in_sz, fp);
	}

	struct cap_call_tail tail;
	if (fread(&tail, sizeof(tail), 1, fp) != 1) {
		free(scal_in);
		free(struct_in);
		return -1;
	}

	uint64_t *cap_scalars = NULL;
	uint8_t *cap_struct = NULL;
	if (tail.scalar_out_cnt) {
		cap_scalars = calloc(tail.scalar_out_cnt, sizeof(uint64_t));
		fread(cap_scalars, sizeof(uint64_t), tail.scalar_out_cnt, fp);
	}
	if (tail.struct_out_sz) {
		cap_struct = calloc(1, tail.struct_out_sz);
		fread(cap_struct, 1, tail.struct_out_sz, fp);
	}

	patch_u64_buf(struct_in, hdr.struct_in_sz);

	uint64_t scal_out[16] = {0};
	uint32_t scal_out_cnt = 16;
	uint8_t live_out[MAX_STRUCT] = {0};
	size_t live_out_sz = tail.struct_out_sz ? tail.struct_out_sz : 0;

	kern_return_t rc = IOConnectCallMethod(conn, hdr.selector,
		scal_in, hdr.scalar_in_cnt,
		struct_in, hdr.struct_in_sz,
		tail.scalar_out_cnt ? scal_out : NULL,
		tail.scalar_out_cnt ? &scal_out_cnt : NULL,
		live_out_sz ? live_out : NULL,
		live_out_sz ? &live_out_sz : NULL);

	printf("[%d] sel=0x%02x rc=0x%x (expected 0x%x) out_sz=%zu\n",
		idx, hdr.selector, rc, tail.rc, live_out_sz);

	if (rc == KERN_SUCCESS && cap_struct && tail.struct_out_sz)
		learn_resource_maps(cap_struct, tail.struct_out_sz,
			live_out, live_out_sz);

	free(scal_in);
	free(struct_in);
	free(cap_scalars);
	free(cap_struct);
	return rc == KERN_SUCCESS ? 0 : 1;
}

static int replay_trap(io_connect_t conn, FILE *fp, int idx)
{
	struct cap_trap_hdr hdr;
	if (fread(&hdr, sizeof(hdr), 1, fp) != 1)
		return -1;

	uint8_t *snap = calloc(1, hdr.snap_sz ? hdr.snap_sz : 1);
	if (hdr.snap_sz)
		fread(snap, 1, hdr.snap_sz, fp);

	struct cap_trap_tail tail;
	if (fread(&tail, sizeof(tail), 1, fp) != 1) {
		free(snap);
		return -1;
	}

	void *buf = NULL;
	size_t alloc_sz = hdr.snap_sz ? hdr.snap_sz + 0x100 : 0;
	if (alloc_sz) {
		posix_memalign(&buf, 0x10, alloc_sz);
		memcpy(buf, snap, hdr.snap_sz);
		patch_u64_buf(buf, hdr.snap_sz);
	}

	uintptr_t p3 = (uintptr_t)buf;
	uintptr_t p4 = hdr.p4 ? p3 + 0x84 : 0;

	kern_return_t rc = IOConnectTrap4(conn, hdr.trap_idx,
		hdr.p1, hdr.p2, p3, p4);

	printf("[%d] trap%u rc=0x%x (expected 0x%x) snap=%u bytes\n",
		idx, hdr.trap_idx, rc, tail.rc, hdr.snap_sz);

	free(snap);
	free(buf);
	return rc == KERN_SUCCESS ? 0 : 1;
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
	    file_hdr.magic != CAP_MAGIC) {
		fprintf(stderr, "invalid capture %s\n", path);
		return 1;
	}

	io_service_t svc = find_agx_service();
	if (!svc) {
		fprintf(stderr, "no AGX accelerator\n");
		return 1;
	}

	io_connect_t conn = 0;
	int idx = 0, fails = 0;

	printf("replaying %s\n", path);

	while (!feof(fp)) {
		uint8_t type;
		if (fread(&type, 1, 1, fp) != 1)
			break;
		fseek(fp, -1, SEEK_CUR);

		if (type == CAP_OPEN) {
			struct cap_open rec;
			fread(&rec, sizeof(rec), 1, fp);
			if (!conn) {
				kern_return_t kr = IOServiceOpen(svc, mach_task_self(),
					rec.client_type, &conn);
				printf("[%d] IOServiceOpen type=0x%x conn=0x%x rc=0x%x\n",
					idx, rec.client_type, conn, kr);
				if (kr != KERN_SUCCESS)
					return 1;
			}
			idx++;
		} else if (type == CAP_CALL) {
			if (!conn)
				return fprintf(stderr, "call before open\n"), 1;
			fails += replay_call(conn, fp, idx++) != 0;
		} else if (type == CAP_TRAP) {
			if (!conn)
				return fprintf(stderr, "trap before open\n"), 1;
			fails += replay_trap(conn, fp, idx++) != 0;
		} else if (type != 0) {
			fprintf(stderr, "bad type %u at op %d\n", type, idx);
			break;
		}
	}

	if (conn)
		IOServiceClose(conn);
	IOObjectRelease(svc);
	fclose(fp);

	printf("done: %d ops, %d failures, %u addr maps\n", idx, fails, nmaps);
	return fails ? 1 : 0;
}
