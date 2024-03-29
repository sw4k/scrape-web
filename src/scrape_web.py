# SPDX-License-Identifier: MIT
# cython: language_level=3
#
# scrape_web.py
# 
# Copyright (C) sw4k
# 
# The `scrape-web` main source file.
# 
import bisect
import os
from pathlib import Path
import requests
import sys
import time
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

class runspace:
    restrict_patterns = []
    ignore_patterns = []
    save_patterns = []
    include_elements = ["a:href"]
    save_all = False
    save_directory = 'saves'
    save_with_paths = False
    max_connection_errors = 4
    max_count = 2147483647
    retry_wait_seconds = 15
    processed_urls = []
    pending_save_urls = []
    pending_scrape_urls = []

class log:
    min_level = 1
    DBG = '\033[236m'
    INF = '\033[250m'
    WRN = '\033[93m'
    ERR = '\033[91m'
    OK = '\033[36m'
    SUCCESS = '\033[32m'
    END = '\033[0m'
    BLD = '\033[1m'
    ULN = '\033[4m'
    SPINNER = ["-", "\\", "|", "/"]
    SPIN_LEVEL = 0
    no_status = False
    def status(msg = ""):
        if (not log.no_status):
            log.SPIN_LEVEL = ((log.SPIN_LEVEL + 1) % 4)
            sys.stdout.write(f"[{log.SPINNER[log.SPIN_LEVEL]}] {msg}\r")
    def ok(msg):
        print(f"{log.OK}{msg}{log.END}")
    def success(msg):
        print(f"{log.SUCCESS}{msg}{log.END}")
    def debug(msg):
        if (log.min_level <= 0):
            print(f"{log.DBG}{msg}{log.END}")
    def info(msg):
        if (log.min_level <= 1):
            print(f"{log.INF}{msg}{log.END}")
    def warn(msg):
        if (log.min_level <= 2):
            print(f"{log.WRN}{msg}{log.END}")
    def error(msg):
        if (log.min_level <= 3):
            print(f"{log.ERR}{msg}{log.END}")

def add_pending_url(url, force = False):
    log.status()
    if (not force):
        if (len(runspace.restrict_patterns) > 0):
            url_parsed = urlparse(url)
            allow_url = False
            for pattern in runspace.restrict_patterns:
                if (url_parsed.netloc.find(pattern) >= 0):
                    allow_url = True
                    break
            if (not allow_url):
                log.debug(f"!!! restricting {url} [{url_parsed.netloc}] [{allow_url}]")
                return
        for ignore in runspace.ignore_patterns:
            if (url.find(ignore) >= 0):
                log.debug(f"!!! ignoring {url}")
                return
        idx = bisect.bisect_left(runspace.processed_urls, url)
        if (idx != len(runspace.processed_urls) and runspace.processed_urls[idx] == url):
            return
    for item in runspace.save_patterns:
        if (url.find(item) >= 0):
            idx = bisect.bisect_left(runspace.pending_save_urls, url)
            if (idx != len(runspace.pending_save_urls) and runspace.pending_save_urls[idx] == url):
                return
            runspace.pending_save_urls.insert(idx, url)
            return
    idx = bisect.bisect_left(runspace.pending_scrape_urls, url)
    if (idx != len(runspace.pending_scrape_urls) and runspace.pending_scrape_urls[idx] == url):
        return
    runspace.pending_scrape_urls.insert(idx, url)
    log.debug(f"+++ add to pending {url}")

def process_content(url, contentType, content):
    if (contentType == None):
        log.warn(f"!!! missing content-type for: {url}")
        return
    if (contentType.find("text/html") < 0 and contentType.find("+xml") < 0 and contentType.find("/xml")):
        # do not parse non-textual content, this does require the server to respond with correct content types
        return
    mltree = BeautifulSoup(content, "lxml")
    for element_info in runspace.include_elements:
        log.status()
        element_parts = element_info.split(":")
        for ele in mltree.find_all(element_parts[0]):
            value = ele.get(element_parts[1])
            if (value == None or value.startswith("#")):
                continue
            if (not value.startswith('http')):
                url_parsed = urlparse(url)
                base_uri = f"{url_parsed.scheme}://{url_parsed.netloc}"
                if (value.startswith('//')):
                    value = f"{url_parsed.scheme}:{value}"
                elif (value.startswith('/') or value.startswith('?')):
                    value = f"{base_uri}{value}"
                else:
                    value = f"{base_uri}/{value}"
            add_pending_url(value)

def save(url):
    bisect.insort_left(runspace.processed_urls, url)
    runspace.pending_save_urls.remove(url)
    # if already exists, no reason to reprocess
    Path(runspace.save_directory).mkdir(parents=True, exist_ok=True)
    filepath = unquote(urlparse(url).path)
    filename = os.path.basename(filepath)
    if (not runspace.save_with_paths):
        filepath = f"{runspace.save_directory}/{filename}"
    elif (filepath.startswith('/')):
        filepath = f"{runspace.save_directory}{filepath}"
    else:
        filepath = f"{runspace.save_directory}/{filepath}"                
    if (os.path.isfile(filepath)):
        log.warn(f"### {filepath}")
        return
    log.status(f"{filepath}\r")
    attempts_remaining = runspace.max_connection_errors
    while (True):
        attempts_remaining -= 1
        try:
            resp = requests.get(url)
            break
        except (Exception):
            if (attempts_remaining <= 0):
                log.error(f"XXX failed: {url}")
                return
            else:
                log.warn(f"..ConnectionError; retrying in {runspace.retry_wait_seconds} seconds")
                time.sleep(runspace.retry_wait_seconds)
    if (resp.status_code == 200):
        contentType = resp.headers["Content-Type"]
        content = resp.content
        with open(filepath, "wb") as f:
            f.write(content)
            f.flush()
        log.success(f"### {filepath}")
        process_content(url, contentType, content)
    else:
        log.error(f"!!! save('{url}') failed with status_code {resp.status_code}")

def scrape(url):
    log.ok(f">>> {url}")
    bisect.insort_left(runspace.processed_urls, url)
    runspace.pending_scrape_urls.remove(url)
    attempts_remaining = runspace.max_connection_errors
    while (True):
        attempts_remaining -= 1
        try:
            resp = requests.get(url)
            break
        except (Exception):
            if (attempts_remaining <= 0):
                log.error(f"XXX failed: {url}")
                return
            else:
                log.warn(f"..ConnectionError; retrying in {runspace.retry_wait_seconds} seconds")
                time.sleep(runspace.retry_wait_seconds)
    if (resp.status_code == 200):
        contentType = resp.headers["Content-Type"]
        content = resp.content
        process_content(url, contentType, content)
    else:
        log.error(f"!!! scrape('{url}') failed with status_code {resp.status_code}")

def print_help():
    log.info("scrape-web v0.3.0\nCopyright (C) sw4k, MIT Licensed\n")
    log.info("Usage:")
    log.info("\tscrape_web [options] --url <string>\n")
    log.info("Options:")
    log.info("\t--verbose\n\t\tIndicates that verbose/debug logging should be enabled.")
    log.info("\t--no-status\n\t\tDisable status messages, useful if processing stdout with another tool.")
    log.info("\t--max-count <number>\n\t\tSet a max count of scrapes to be performed.")
    log.info("\t--restrict <hostname>\n\t\t*MULTI* When scraping URLs, if the host-part does not match this string the URL will be ignored/skipped.")
    log.info("\t--ignore <substring>\n\t\t*MULTI* When scraping URLs, if this substring matches a URL the URL will be ignored/skipped.")
    log.info("\t--save <substring>\n\t\t*MULTI* When scraping URLs, if this substring matches the URL the content found at the URL will be downloaded and saved locally. ")
    log.info("\t--save-all\n\t\tIndicates that all content scraped should be saved. This may still require the use of `--element` and `--preserve-paths` to exhibit the expected results.")
    log.info("\t--out-dir <path>\n\t\tWhen used in conjuction with `--save` this specifies where files will be saved, by default they are saved to 'saves/`. This may be a relative or absolute path.")
    log.info("\t--preserve-paths\n\t\tIndicates that server paths should be appended to local paths whens saving, by default server paths are discarded.")
    log.info(f"\t--max-connection-errors <number>\n\t\tSets the maximum number of retries that will be performed for a single scrape attempts before giving up. The default is {runspace.max_connection_errors}.")
    log.info(f"\t--retry-wait-seconds <number>\n\t\tSets the number of seconds to wait when there is a connection error before a retry attempt is made. The default is {runspace.retry_wait_seconds}.")
    log.info("\t--element <name>:<attr>\n\t\t*MULTI* When scraping URLs, include urls represented by elements named `name` with URLs come from `attr`; the colon is a separator of `name` and `attr`.")
    log.info("\nNOTE: Options with '*MULTI*' in the description may be specified more than once.")

def print_settings(url):
    log.info("======================")
    log.info("== Settings Summary ==")
    log.info("======================")
    if (runspace.save_all):
        log.info("Saving all content (using `--save-all`, are you using using `--preserve-paths`?)")
    elif (len(runspace.save_patterns) > 0):
        log.info("Saving content matching substrings:")
        for item in runspace.save_patterns:
            log.info(f"\t{item}")
    else:
        log.warn("Not Saving any content (use `--save` or `--save-all`)")
    if (len(runspace.restrict_patterns) > 0):
        log.info("Restricting to URLS matching substrings:")
        for item in runspace.restrict_patterns:
            log.info(f"\t{item}")
    else:
        log.warn(f"Not ignoring any URLs {log.BLD}!BEWARE! you may crawl out of the target website!{log.END} (use `--verbose` and `--ignore`)")
    if (len(runspace.ignore_patterns) > 0):
        log.info("Ignoring URLS matching substrings:")
        for item in runspace.ignore_patterns:
            log.info(f"\t{item}")
    else:
        log.warn(f"Not ignoring any URLs {log.BLD}!BEWARE! you may crawl out of the target website!{log.END} (use `--verbose` and `--ignore`)")
    log.info("Scraping URLS from the following elements/attributes (use `--include` to add more):")
    for item in runspace.include_elements:
        log.info(f"\t{item}")
    log.info("General Settings:")
    if (runspace.max_count != 2147483647):
        log.info(f"\t--max-count {runspace.max_count}")
    log.info(f"\t--max-connection-errors {log.SUCCESS}{runspace.max_connection_errors}")
    log.info(f"\t--retry-wait-seconds {log.SUCCESS}{runspace.retry_wait_seconds}")
    log.info(f"\t--save-all {log.SUCCESS}{runspace.save_all}")
    log.info(f"\t--out-dir {log.SUCCESS}{runspace.save_directory}")
    log.info(f"\t--save-with-paths {log.SUCCESS}{runspace.save_with_paths}")
    log.info(f"\t--url {log.SUCCESS}{url}")
    log.info("======================")
    log.info("======================")
    log.info("======================")

def parse_commandline():
    url = "about:blank"
    args = sys.argv[0:]
    argc = len(args)
    for argi in range(1, len(args)):
        arg = args[argi]
        if (arg == "--url"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--url <string>`")
                return 2
            url = args[argi]
        elif (arg == "--max-count"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--max-count <number>`")
                return 2
            runspace.max_count = int(args[argi])
        elif (arg == "--restrict"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--restrict <substring>`")
                return 2
            runspace.restrict_patterns.append(args[argi])
        elif (arg == "--ignore"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--ignore <substring>`")
                return 2
            runspace.ignore_patterns.append(args[argi])
        elif (arg == "--element"):
            argi += 1             
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--element <name>:<attr>`")
                return 2
            ele_parts = args[argi].split(":")
            if (ele_parts == None or len(ele_parts) != 2):
                print_help()
                log.error(f"ERR(2): parameter for `--element <name>:<attr>` is malformed")
                return 2
            runspace.include_elements.append(args[argi])
        elif (arg == "--save"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--save <substring>`")
                return 2
            runspace.save_patterns.append(args[argi])
        elif (arg == "--save-all"):
            runspace.save_all = True
        elif (arg == "--verbose"):
            log.min_level = 0
        elif (arg == "--no-status"):
            log.no_status = True
        elif (arg == "--out-dir"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--out-dir <path>`")
                return 2
            runspace.save_directory = args[argi]
        elif (arg == "--preserve-paths"):
            runspace.save_with_paths = True
        elif (arg == "--max-connection-errors"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--max-connection-errors <number>`")
                return 2
            runspace.max_connection_errors = int(args[argi])
        elif (arg == "--retry-wait-seconds"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--retry-wait-seconds <number>`")
                return 2
            runspace.retry_wait_seconds = int(args[argi])
        elif (arg == "--help"):
            print_help()
            exit(0)
        else:
            log.warn(f"Unrecognized argument: `{args[argi]}`")
    return url

def run():
    url = parse_commandline()
    if (url == "about:blank"):
        print_help()
        log.error("ERR(1): no url specified")
        exit(1)
    print_settings(url)
    for i in reversed(range(1, 6)):
        sys.stdout.write(f"..starting in {i}..\r")        
        time.sleep(1)
    print("")
    add_pending_url(url, True)
    processed_count = 0
    while (True):
        log.status()
        processed_count += 1
        if (runspace.max_count < processed_count):
            log.warn("!!! maximum number of scrapes performed, exiting.")
            return
        if (len(runspace.pending_save_urls) > 0):
            save(runspace.pending_save_urls[0])
        elif (len(runspace.pending_scrape_urls) > 0):
            scrape(runspace.pending_scrape_urls[0])
        else:
            log.info(f"Done. Processed {processed_count} URLs.")
            return

run()
