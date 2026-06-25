// Minimal Metal render: draw a red triangle into an 8x8 shared texture.
// Capture: CAPTURE_PATH=tri.cap DYLD_INSERT_LIBRARIES=./iokit_capture.dylib ./metal_tri

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static const char *kSource =
	"#include <metal_stdlib>\n"
	"using namespace metal;\n"
	"struct Vertex { float2 pos; };\n"
	"vertex float4 vtx(const device Vertex *v [[buffer(0)]], uint vid [[vertex_id]]) {\n"
	"    return float4(v[vid].pos, 0.0, 1.0);\n"
	"}\n"
	"fragment float4 frag(float4 pos [[position]]) {\n"
	"    return float4(1.0, 0.0, 0.0, 1.0);\n"
	"}\n";

static int check_pixels(const uint8_t *px, NSUInteger w, NSUInteger h)
{
	// Center pixel should be red in BGRA8Unorm.
	NSUInteger cx = w / 2, cy = h / 2;
	NSUInteger off = (cy * w + cx) * 4;
	uint8_t b = px[off + 0];
	uint8_t g = px[off + 1];
	uint8_t r = px[off + 2];
	uint8_t a = px[off + 3];
	printf("center pixel BGRA %u %u %u %u\n", b, g, r, a);
	return (r > 200 && g < 50 && b < 50 && a > 200);
}

int main(int argc, char **argv)
{
	(void)argc; (void)argv;

	@autoreleasepool {
		const NSUInteger W = 8, H = 8;

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

		id<MTLFunction> vs = [lib newFunctionWithName:@"vtx"];
		id<MTLFunction> fs = [lib newFunctionWithName:@"frag"];
		id<MTLRenderPipelineState> pso =
			[dev newRenderPipelineStateWithDescriptor:({
				MTLRenderPipelineDescriptor *d = [MTLRenderPipelineDescriptor new];
				d.vertexFunction = vs;
				d.fragmentFunction = fs;
				d.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
				d;
			}) error:&err];
		if (!pso) {
			fprintf(stderr, "pso failed: %s\n", [[err localizedDescription] UTF8String]);
			return 1;
		}

		MTLTextureDescriptor *td = [MTLTextureDescriptor new];
		td.textureType = MTLTextureType2D;
		td.pixelFormat = MTLPixelFormatBGRA8Unorm;
		td.width = W;
		td.height = H;
		td.depth = 1;
		td.mipmapLevelCount = 1;
		td.sampleCount = 1;
		td.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
		td.storageMode = MTLStorageModeShared;
		id<MTLTexture> tex = [dev newTextureWithDescriptor:td];

		// Big-triangle covering the full viewport.
		struct { float x, y; } verts[] = {
			{ -1.f, -1.f },
			{  3.f, -1.f },
			{ -1.f,  3.f },
		};
		id<MTLBuffer> vbuf = [dev newBufferWithBytes:verts length:sizeof(verts)
			options:MTLResourceStorageModeShared];

		MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
		pass.colorAttachments[0].texture = tex;
		pass.colorAttachments[0].loadAction = MTLLoadActionClear;
		pass.colorAttachments[0].storeAction = MTLStoreActionStore;
		pass.colorAttachments[0].clearColor = MTLClearColorMake(0, 0, 0, 1);

		id<MTLCommandQueue> queue = [dev newCommandQueue];
		id<MTLCommandBuffer> cb = [queue commandBuffer];
		id<MTLRenderCommandEncoder> enc = [cb renderCommandEncoderWithDescriptor:pass];
		[enc setRenderPipelineState:pso];
		[enc setVertexBuffer:vbuf offset:0 atIndex:0];
		[enc drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
		[enc endEncoding];
		[cb commit];
		[cb waitUntilCompleted];

		uint8_t pixels[W * H * 4];
		memset(pixels, 0, sizeof(pixels));
		[tex getBytes:pixels bytesPerRow:W * 4
			fromRegion:MTLRegionMake2D(0, 0, W, H) mipmapLevel:0];

		int ok = check_pixels(pixels, W, H);
		printf("triangle %s\n", ok ? "PASS" : "FAIL");

		const char *ppm = getenv("METAL_TRI_PPM");
		if (ppm && ppm[0]) {
			FILE *fp = fopen(ppm, "wb");
			if (fp) {
				fprintf(fp, "P6\n%lu %lu\n255\n", (unsigned long)W, (unsigned long)H);
				for (NSUInteger i = 0; i < W * H; i++)
					fputc(pixels[i * 4 + 2], fp), fputc(pixels[i * 4 + 1], fp),
						fputc(pixels[i * 4 + 0], fp);
				fclose(fp);
				printf("wrote %s\n", ppm);
			}
		}

		return ok ? 0 : 2;
	}
}
