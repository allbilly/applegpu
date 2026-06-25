// Minimal Metal compute: out[i] = a[i] + b[i]
// Run under capture: CAPTURE_PATH=add.cap DYLD_INSERT_LIBRARIES=./iokit_capture.dylib ./metal_add

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdio.h>
#include <string.h>

static const char *kSource =
	"#include <metal_stdlib>\n"
	"using namespace metal;\n"
	"kernel void add_arrays(device const float *a [[buffer(0)]],\n"
	"                       device const float *b [[buffer(1)]],\n"
	"                       device float *out [[buffer(2)]],\n"
	"                       uint i [[thread_position_in_grid]]) {\n"
	"    out[i] = a[i] + b[i];\n"
	"}\n";

int main(int argc, char **argv)
{
	(void)argc; (void)argv;

	@autoreleasepool {
		const NSUInteger n = 4;
		float ha[] = { 1, 2, 3, 4 };
		float hb[] = { 10, 20, 30, 40 };
		float ho[4] = {0};

		id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
		if (!dev) {
			fprintf(stderr, "no Metal device\n");
			return 1;
		}

		NSError *err = nil;
		id<MTLLibrary> lib = [dev newLibraryWithSource:@(kSource) options:nil error:&err];
		if (!lib) {
			fprintf(stderr, "compile failed: %s\n", [[err localizedDescription] UTF8String]);
			return 1;
		}

		id<MTLFunction> fn = [lib newFunctionWithName:@"add_arrays"];
		id<MTLComputePipelineState> pso =
			[dev newComputePipelineStateWithFunction:fn error:&err];
		if (!pso) {
			fprintf(stderr, "pso failed: %s\n", [[err localizedDescription] UTF8String]);
			return 1;
		}

		id<MTLBuffer> bufa = [dev newBufferWithBytes:ha length:sizeof(ha) options:MTLResourceStorageModeShared];
		id<MTLBuffer> bufb = [dev newBufferWithBytes:hb length:sizeof(hb) options:MTLResourceStorageModeShared];
		id<MTLBuffer> bufo = [dev newBufferWithBytes:ho length:sizeof(ho) options:MTLResourceStorageModeShared];

		id<MTLCommandQueue> queue = [dev newCommandQueue];
		id<MTLCommandBuffer> cb = [queue commandBuffer];
		id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
		[enc setComputePipelineState:pso];
		[enc setBuffer:bufa offset:0 atIndex:0];
		[enc setBuffer:bufb offset:0 atIndex:1];
		[enc setBuffer:bufo offset:0 atIndex:2];
		[enc dispatchThreadgroups:MTLSizeMake(1, 1, 1)
			threadsPerThreadgroup:MTLSizeMake(n, 1, 1)];
		[enc endEncoding];
		[cb commit];
		[cb waitUntilCompleted];

		memcpy(ho, bufo.contents, sizeof(ho));
		printf("result:");
		for (NSUInteger i = 0; i < n; i++)
			printf(" %.0f", ho[i]);
		printf("\n");

		int ok = (ho[0] == 11 && ho[1] == 22 && ho[2] == 33 && ho[3] == 44);
		return ok ? 0 : 2;
	}
}
