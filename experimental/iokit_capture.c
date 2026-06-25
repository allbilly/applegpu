// DYLD interpose: record AGX IOKit traffic to a binary file for replay.
// Set CAPTURE_PATH=/path/to/capture.bin before running the Metal app.

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <IOKit/IOKitLib.h>

#define CAP_MAGIC 0x43584741 /* AGXC */
#define CAP_VERSION 1

enum cap_type {
	CAP_OPEN = 1,
	CAP_CALL = 2,
	CAP_TRAP = 3,
};

struct cap_hdr {
	uint32_t magic;
	uint32_t version;
	uint32_t count;
	uint32_t _pad;
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
	/* followed by: scalars[scalar_in_cnt], struct_in[struct_in_sz] */
};

struct cap_call_tail {
	int32_t rc;
	uint32_t scalar_out_cnt;
	uint32_t struct_out_sz;
	/* followed by: scalars[scalar_out_cnt], struct_out[struct_out_sz] */
};

struct cap_trap_hdr {
	uint8_t type;
	uint8_t _pad[3];
	uint32_t conn;
	uint32_t trap_idx;
	uint64_t p1, p2, p3, p4;
	uint32_t snap_sz;
	/* followed by snap bytes */
};

struct cap_trap_tail {
	int32_t rc;
};

static int cap_fd = -1;
static io_connect_t gpu_conn = 0;

static void cap_open_file(void)
{
	if (cap_fd >= 0)
		return;

	const char *path = getenv("CAPTURE_PATH");
	if (!path || !path[0])
		return;

	cap_fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (cap_fd < 0) {
		fprintf(stderr, "capture: open %s failed\n", path);
		return;
	}

	struct cap_hdr hdr = { CAP_MAGIC, CAP_VERSION, 0, 0 };
	write(cap_fd, &hdr, sizeof(hdr));
}

static void cap_write(const void *buf, size_t len)
{
	if (cap_fd < 0)
		return;
	write(cap_fd, buf, len);
}

static int is_gpu_conn(io_connect_t conn)
{
	return gpu_conn != 0 && conn == gpu_conn;
}

static kern_return_t real_IOConnectCallMethod(
	mach_port_t connection, uint32_t selector,
	const uint64_t *input, uint32_t inputCnt,
	const void *inputStruct, size_t inputStructCnt,
	uint64_t *output, uint32_t *outputCnt,
	void *outputStruct, size_t *outputStructCntP);

static kern_return_t my_IOServiceOpen(
	io_service_t service, task_port_t owner, uint32_t type, io_connect_t *conn)
{
	kern_return_t rc = IOServiceOpen(service, owner, type, conn);

	if (type == 0x100005 && rc == KERN_SUCCESS && conn && *conn) {
		gpu_conn = *conn;
		cap_open_file();
		if (cap_fd >= 0) {
			struct cap_open rec = {
				.type = CAP_OPEN,
				.client_type = type,
				.rc = rc,
				.conn = *conn,
			};
			cap_write(&rec, sizeof(rec));
		}
	}
	return rc;
}

static kern_return_t my_IOConnectCallMethod(
	mach_port_t connection, uint32_t selector,
	const uint64_t *input, uint32_t inputCnt,
	const void *inputStruct, size_t inputStructCnt,
	uint64_t *output, uint32_t *outputCnt,
	void *outputStruct, size_t *outputStructCntP)
{
	int record = cap_fd >= 0 && is_gpu_conn(connection) && selector <= 0x40;

	uint64_t scal_in[16] = {0};
	uint8_t *struct_in_copy = NULL;
	uint8_t *struct_out_copy = NULL;
	size_t struct_out_sz = outputStructCntP ? *outputStructCntP : 0;

	uint32_t rec_in_cnt = inputCnt > 16 ? 16 : inputCnt;
	if (record) {
		if (rec_in_cnt)
			memcpy(scal_in, input, rec_in_cnt * sizeof(uint64_t));
		if (inputStruct && inputStructCnt) {
			struct_in_copy = malloc(inputStructCnt);
			memcpy(struct_in_copy, inputStruct, inputStructCnt);
		}
		if (outputStruct && struct_out_sz)
			struct_out_copy = calloc(1, struct_out_sz);
	}

	kern_return_t rc = real_IOConnectCallMethod(
		connection, selector, input, inputCnt,
		inputStruct, inputStructCnt,
		output, outputCnt,
		outputStruct, outputStructCntP);

	if (record) {
		struct cap_call_hdr hdr = {
			.type = CAP_CALL,
			.conn = connection,
			.selector = selector,
			.scalar_in_cnt = rec_in_cnt,
			.struct_in_sz = inputStructCnt,
		};
		cap_write(&hdr, sizeof(hdr));
		if (rec_in_cnt)
			cap_write(scal_in, rec_in_cnt * sizeof(uint64_t));
		if (inputStructCnt)
			cap_write(struct_in_copy, inputStructCnt);

		uint32_t out_cnt = outputCnt ? *outputCnt : 0;
		size_t out_struct_sz = outputStructCntP ? *outputStructCntP : 0;
		struct cap_call_tail tail = {
			.rc = rc,
			.scalar_out_cnt = out_cnt,
			.struct_out_sz = out_struct_sz,
		};
		cap_write(&tail, sizeof(tail));
		if (out_cnt && output)
			cap_write(output, out_cnt * sizeof(uint64_t));
		if (out_struct_sz && outputStruct) {
			memcpy(struct_out_copy, outputStruct, out_struct_sz);
			cap_write(struct_out_copy, out_struct_sz);
		}
		free(struct_in_copy);
		free(struct_out_copy);
	}

	return rc;
}

static kern_return_t my_IOConnectTrap4(
	io_connect_t connect, uint32_t index,
	uintptr_t p1, uintptr_t p2, uintptr_t p3, uintptr_t p4)
{
	int record = cap_fd >= 0 && is_gpu_conn(connect);
	uint32_t snap_sz = 0;
	uint8_t snap[256];

	if (record && p3 && p2) {
		snap_sz = p2 > sizeof(snap) ? sizeof(snap) : (uint32_t)p2;
		memcpy(snap, (const void *)p3, snap_sz);
	}

	kern_return_t rc = IOConnectTrap4(connect, index, p1, p2, p3, p4);

	if (record) {
		struct cap_trap_hdr hdr = {
			.type = CAP_TRAP,
			.conn = connect,
			.trap_idx = index,
			.p1 = p1, .p2 = p2, .p3 = p3, .p4 = p4,
			.snap_sz = snap_sz,
		};
		cap_write(&hdr, sizeof(hdr));
		if (snap_sz)
			cap_write(snap, snap_sz);
		struct cap_trap_tail tail = { .rc = rc };
		cap_write(&tail, sizeof(tail));
	}

	return rc;
}

__attribute__((used, section("__DATA,__interpose"))) static const struct {
	const void *n, *o;
} _iccm = { my_IOConnectCallMethod, IOConnectCallMethod };
__attribute__((used, section("__DATA,__interpose"))) static const struct {
	const void *n, *o;
} _iopen = { my_IOServiceOpen, IOServiceOpen };
__attribute__((used, section("__DATA,__interpose"))) static const struct {
	const void *n, *o;
} _itrap = { my_IOConnectTrap4, IOConnectTrap4 };

kern_return_t real_IOConnectCallMethod(
	mach_port_t connection, uint32_t selector,
	const uint64_t *input, uint32_t inputCnt,
	const void *inputStruct, size_t inputStructCnt,
	uint64_t *output, uint32_t *outputCnt,
	void *outputStruct, size_t *outputStructCntP)
{
	return IOConnectCallMethod(connection, selector, input, inputCnt,
		inputStruct, inputStructCnt, output, outputCnt,
		outputStruct, outputStructCntP);
}
