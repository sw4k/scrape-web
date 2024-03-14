# SPDX-License-Identifier: MIT
PY := $(shell which python3)
PYVERSION := $(shell $(PY) -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYPREFIX := $(shell $(PY) -c "import sys; print(sys.prefix)")
CY := $(shell which cython3)
CC := $(shell which gcc)
CFLAGS := $(shell python3-config --cflags) $(CFLAGS)
KERNEL_VERSION := $(shell uname -r)
INCLUDES := \
	$(shell python3-config --includes)
LIBS := \
	$(shell python3-config --ldflags) \
	-lpython$(PYVERSION)

SRCDIR := src
OBJDIR := obj
BINDIR := bin
INSTALLDIR := install

.PHONY: clean all prepare-install install uninstall

build: $(BINDIR)/scrape-web
	
rebuild: clean build

$(OBJDIR) $(BINDIR):
	mkdir -p $@

clean:
	rm -f release-files.tar.gz
	rm -f $(INSTALLDIR)/scrape-web
	rm -rf $(OBJDIR)
	rm -rf $(BINDIR)

$(OBJDIR)/%.c: $(OBJDIR) $(SRCDIR)/%.py
	$(CY) --output-file $(OBJDIR)/$(@F) --embed $(SRCDIR)/$*.py

$(OBJDIR)/%.o: $(OBJDIR) $(OBJDIR)/%.c
	$(CC) -c $(OBJDIR)/$*.c $(INCLUDES) $(CFLAGS) -o $(OBJDIR)/$(@F)

OBJECTS := \
	$(OBJDIR)/scrape_web.o

$(BINDIR)/scrape-web: $(BINDIR) $(OBJECTS)
	$(CC) $(OBJECTS) $(LIBS) -o $(BINDIR)/scrape-web

prepare-install: build
	cp -f $(BINDIR)/scrape-web $(INSTALLDIR)/scrape-web
	cd $(INSTALLDIR) && tar --gzip -cf ../release-files.tar.gz ./

install: prepare-install
	cd $(INSTALLDIR) && ./install.sh

uninstall:
	cd $(INSTALLDIR) && ./uninstall.sh
