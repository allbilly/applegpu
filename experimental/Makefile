CC = clang
CFLAGS = -g -Wall -Wextra -O2
FRAMEWORKS = -framework IOKit

.PHONY: all clean capture capture-tri replay replay-py run run-py run-tri standalone standalone-tri run-standalone run-standalone-tri

all: iokit_capture.dylib metal_add metal_tri replay

standalone-tri: replay-py
	python3 cap2standalone.py tri.cap -o ../examples/tri.py

run-standalone-tri: standalone-tri
	python3 ../examples/tri.py

standalone: replay-py
	python3 cap2standalone.py add.cap -o ../examples/add.py

run-standalone: standalone
	python3 ../examples/add.py

replay-py:
	chmod +x replay.py

run-py: capture replay-py
	python3 replay.py add.cap

iokit_capture.dylib: iokit_capture.c
	$(CC) $(CFLAGS) -dynamiclib $(FRAMEWORKS) -o $@ $<

metal_add: metal_add.m
	$(CC) $(CFLAGS) -framework Metal -framework Foundation -o $@ $<

metal_tri: metal_tri.m
	$(CC) $(CFLAGS) -framework Metal -framework Foundation -o $@ $<

replay: replay.c
	$(CC) $(CFLAGS) $(FRAMEWORKS) -o $@ $<

capture: all
	CAPTURE_PATH=$(CURDIR)/add.cap DYLD_INSERT_LIBRARIES=$(CURDIR)/iokit_capture.dylib ./metal_add
	@echo "wrote add.cap ($$(wc -c < add.cap) bytes)"

capture-tri: all
	CAPTURE_PATH=$(CURDIR)/tri.cap DYLD_INSERT_LIBRARIES=$(CURDIR)/iokit_capture.dylib ./metal_tri
	@echo "wrote tri.cap ($$(wc -c < tri.cap) bytes)"

run-tri: capture-tri
	python3 replay.py tri.cap

run: capture
	./replay add.cap

clean:
	rm -f iokit_capture.dylib metal_add metal_tri replay add.cap tri.cap
