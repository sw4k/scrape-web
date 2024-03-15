# SPDX-License-Identifier: MIT
#
# scrape_web.py
# 
# Copyright (C) sw4k
# 
# The `scrape-web` main source file.
# 
import os
from pathlib import Path
import requests
import sys
import time
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

class runspace:
    ignore_urls = []
    include_elements = ["a:href"]
    max_connection_errors = 3
    max_count = 2147483647
    pending_urls = []
    retry_wait_seconds = 5
    save_all = False
    save_urls = []
    save_directory = 'saves'
    save_with_paths = False
    scraped_urls = []

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

def try_save(url):
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
        return "skip", "skip"
    should_save = runspace.save_all
    if (not should_save):
        for item in runspace.save_urls:
            if (url.find(item) >= 0):
                should_save = True
    if (should_save):
        attempts_remaining = runspace.max_connection_errors
        while (True):
            attempts_remaining -= 1
            try:
                resp = requests.get(url)
                break
            except (Exception):
                if (attempts_remaining <= 0):
                    log.error(f"XXX failed: {url}")
                    return None, None
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
            return contentType, content
        else:
            log.error(f"do_save('{url}') failed with status_code {resp.status_code}")
    return None, None

def add_to_pending(url, force = False):
    if (not force):
        for ignore in runspace.ignore_urls:
            if (url.find(ignore) >= 0):
                log.debug(f"!!! ignoring {url}")
                return
        for item in runspace.scraped_urls:
            if (item == url):
                return
    for item in runspace.pending_urls:
        if (item == url):
            return
    log.debug(f"+++ add to pending {url}")
    for item in runspace.save_urls:
        if (url.find(item) >= 0):
            runspace.pending_urls.insert(0, url)
            return
    runspace.pending_urls.append(url)

def scrape(url):
    runspace.scraped_urls.append(url)
    runspace.pending_urls.remove(url)
    contentType, content = try_save(url)
    if (contentType == "skip" and content == "skip"):
        return
    if (contentType == None or content == None):
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
        contentType = resp.headers["Content-Type"]
        content = resp.content
        if (contentType == None):
            log.warn(f"!!! missing content-type for: {url}")
            return
    if (contentType.find("text/html") < 0 and contentType.find("+xml") < 0 and contentType.find("/xml")):
        # do not parse non-textual content, this does require the server to respond with correct content types
        return
    log.ok(f">>> {url}")
    html = BeautifulSoup(resp.content, "lxml")
    for element_info in runspace.include_elements:
        element_parts = element_info.split(":")
        for ele in html.find_all(element_parts[0]):
            value = ele.get(element_parts[1])
            if (value == None):
                continue
            if (not value.startswith('http')):
                url_parsed = urlparse(url)
                base_uri = f"{url_parsed.scheme}://{url_parsed.netloc}"
                if (value.startswith('/')):
                    value = f"{base_uri}{value}"
                elif (value.endswith('.html') or value.endswith('.htm')):
                    value = f"{base_uri}/{value}"
            if (not value.startswith('http')):
                log.error(f"!!! scraped bad URL `{value}` from element `{element_info}` at `{url}`, discarded.")
            else:
                add_to_pending(value)

def print_help():
    log.info("scrape-web v0.3.0\nCopyright (C) sw4k, MIT Licensed\n")
    log.info("Usage:")
    log.info("\tscrape_web [options] --url <string>\n")
    log.info("Options:")
    log.info("\t--max-count <number>\n\t\tSet a max count of scrapes to be performed.")
    log.info("\t--ignore <substring>\n\t\t*MULTI* When scraping URLs, if this substring matches a URL the URL will be ignored/skipped.")
    log.info("\t--save <substring>\n\t\t*MULTI* When scraping URLs, if this substring matches the URL the content found at the URL will be downloaded and saved locally. ")
    log.info("\t--save-all\n\t\tIndicates that all content scraped should be saved. This may still require the use of `--element` and `--preserve-paths` to exhibit the expected results.")
    log.info("\t--verbose\n\t\tIndicates that verbose/debug logging should be enabled.")
    log.info("\t--out-dir <path>\n\t\tWhen used in conjuction with `--save` this specifies where files will be saved, by default they are saved to 'saves/`. This may be a relative or absolute path.")
    log.info("\t--preserve-paths\n\t\tIndicates that server paths should be appended to local paths whens saving, by default server paths are discarded.")
    log.info(f"\t--max-connection-errors <number>\n\t\tSets the maximum number of retries that will be performed for a single scrape attempts before giving up. The default is {runspace.max_connection_errors}.")
    log.info(f"\t--retry-wait-seconds <number>\n\t\tSets the number of seconds to wait when there is a connection error before a retry attempt is made. The default is {runspace.retry_wait_seconds}.")
    log.info("\t--element <name:attr>\n\t\t*MULTI* When scraping URLs, include urls represented by elements named `name` with URLs come from `attr`; the colon is a separator of `name` and `attr`.")
    log.info("\nNOTE: Options with '*MULTI*' in the description may be specified more than once.")

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
        elif (arg == "--ignore"):
            argi += 1
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--ignore <substring>`")
                return 2
            runspace.ignore_urls.append(args[argi])
        elif (arg == "--element"):
            argi += 1             
            if (argi >= argc):
                print_help()
                log.error(f"ERR(2): missing required parameter for `--ignore <substring>`")
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
            runspace.save_urls.append(args[argi])
        elif (arg == "--save-all"):
            runspace.save_all = True
        elif (arg == "--verbose"):
            log.min_level = 0
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
    return url

def run():
    url = parse_commandline()
    if (url == "about:blank"):
        print_help()
        log.error("ERR(1): no url specified")
        exit(1)
    add_to_pending(url, True)
    while (runspace.max_count > 0 and len(runspace.pending_urls) > 0):
        runspace.max_count -= 1
        if (runspace.max_count <= 0):
            log.warn("!!! maximum number of scrapes performed, exiting.")
        else:
            scrape(runspace.pending_urls[0])

run()
