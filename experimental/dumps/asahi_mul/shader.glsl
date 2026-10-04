#version 310 es
layout(local_size_x=4) in;
layout(std430, binding=0) readonly buffer InputA { float a[]; };
layout(std430, binding=1) readonly buffer InputB { float b[]; };
layout(std430, binding=2) writeonly buffer Output { float c[]; };
void main() {
    uint i = gl_GlobalInvocationID.x;
    c[i] = a[i] * b[i];
}
