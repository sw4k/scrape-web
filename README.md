This repository contains the code for `scrape-web` a quick-and-dirty python tool for scraping content from websites. It will walk every URL discovered given a start URL.

There are command-line options to ignore URLs matching a substring: `--ignore`

This tool becomes more useful if you use the `--save` option, but without saving anything it is also useful for dumping discovered URLs to the console for processing through a tool such as `sed`, `grep`, etc.

## Usage

The precompiled binary should be installed to `$PATH`, so it can be executed as follows:

```text
Usage:
        scrape_web [options] --url <url>

Options:
        --verbose
                Indicates that verbose/debug logging should be enabled.
        --no-status
                Disable status messages, useful if processing stdout with another tool.
        --max-connection-errors <number>
                Sets the maximum number of retries that will be performed for a single scrape attempts before giving up. The default is 3.
        --retry-wait-seconds <number>
                Sets the number of seconds to wait when there is a connection error before a retry attempt is made. The default is 5.
        --max-count <number>
                Set a max count of scrapes to be performed.
        --ignore <substring>
                *MULTI* When scraping URLs, if this substring matches a URL the URL will be ignored/skipped.
        --save <substring>
                *MULTI* When scraping URLs, if this substring matches the URL the content found at the URL will be downloaded and saved locally. 
        --save-all
            Indicates that all content scraped should be saved. This may still require the use of `--element` and `--preserve-paths` to exhibit the expected results.
        --out-dir <path>
                When used in conjuction with `--save` this specifies where files will be saved, by default they are saved to 'saves/`. This may be a relative or absolute path.
        --preserve-paths
                Indicates that server paths should be appended to local paths whens saving, by default server paths are discarded.
        --element <name>:<attr>
                *MULTI* When scraping URLs, include urls represented by elements named `name` with URLs come from `attr`; the colon is a separator of `name` and `attr`.

NOTE: Options with '*MULTI*' in the description may be specified more than once.
```

## Dependencies

`scrape-web` is a python3 program, you will need `pipenv`, `pip`, and `python3` to run directly from sources:

```bash
sudo apt install -y python3-full python3-pip pipenv
```

Once dependencies are installed you can spawn a `pipenv shell`:

```bash
pipenv shell
```

From within `pipenv shell` you can install modules and run the tool:

```bash
pipenv install
python3 src/scrape-web.py --help
```

## Compiling

Compilation assumes you have all the necessary Python3 dependencies mentioned above. To compile to a standalone binary depends on `cython3` and `gcc`, which may require additional dependencies to be installed:

```bash
sudo apt install -y build-essential cython3 cython-doc
```

Once you have the required tools, you should be able to leverage `make`. Doing this from within a pipenv shell should ensure the correct python versions are being used during compilation.

```bash
pipenv shell
make build
```

## Installation

Installation assumes you were able to successfully build following the instructions above, if so there is a `make install` target you can use, you will probably have to run it via `sudo`:

> WARNING: This will install `beautifulsoup4` and 'lxml' modules globally using pip, the cython-compiled binary will not run correctly without this. For most users this will not be a problem because it is not a normal dependency which python3 relies on, but if you depend on a specific global version you may want to edit the install script before continuing.

```bash
sudo make install
```

You can also uninstall:

> WARNING: This will uninstall `beautifulsoup4` and 'lxml' globally using pip, since the install script installs it. For most users this will not be a problem, but if you depend on this package globally you may want to edit the uninstall script before continuing.


```bash
sudo make uninstall
```

## Report Issues or Submit Improvements

If you discover any problems or want to improve the code, visit the project page on github at [https://github.com/sw4k/scrape-web](https://github.com/sw4k/scrape-web).

