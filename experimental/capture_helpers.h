#ifndef APPLEGPU_CAPTURE_HELPERS_H
#define APPLEGPU_CAPTURE_HELPERS_H

#include <dlfcn.h>
#include <stddef.h>

/* The capture dylib exports this hook. Looking it up dynamically keeps the
 * Metal fixtures runnable without linking against the interposer. */
static inline void
agx_capture_expected(const void *address, size_t size)
{
	typedef void (*capture_fn)(const void *, size_t);
	capture_fn fn = (capture_fn)dlsym(RTLD_DEFAULT, "AGXCaptureExpected");
	if (fn)
		fn(address, size);
}

#endif
