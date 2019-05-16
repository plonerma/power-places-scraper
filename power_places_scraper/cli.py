import argparse
import sys
import os
import json
import tqdm

from power_places_scraper import scrape_osm, scrape_google
from power_places_scraper.util import (
    load_bounding_box, test_connection, init_proxy, current_time_str)


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument('source_path', help="Source file or directory (if"
                        "source_path is a directory, all files in it will be"
                        "used recursively).")

    parser.add_argument('target_path', help="Output file or directory")

    parser.add_argument('--osm', action='store_true',
                        help="Get data from OpenStreetMap")

    parser.add_argument('--google', action='store_true',
                        help="Get data from the google search (if neither"
                        "--osm nor --google is set, both are used).")

    parser.add_argument('--proxy', help="Use a proxy, format: <host>:<port>",
                        default=None, dest="proxy")

    parser.add_argument('--tor', help="Use default TOR proxy settings (if both"
                        "options are set, --proxy has precedence).",
                        action='store_true', dest="proxy_tor")

    return parser.parse_args(args)


def parse_proxy(args):
    """Convert string to proxy host and port."""
    # if both proxy options are set, --proxy has precedence
    proxy_host, proxy_port = None, None
    if args.proxy:
        proxy_host, proxy_port = args.proxy.split(":")
        proxy_port = int(proxy_port)
    elif args.proxy_tor:
        proxy_host, proxy_port = "localhost", 9150
    return proxy_host, proxy_port


def crawl_file(source, target, use_osm, use_google):
    if os.path.isdir(target):
        basename = os.path.basename(source)
        name = os.path.splitext(basename)[0] + '.json'
        target = os.path.join(target, name)

    if use_osm:
        # get bounding box from source file
        bounding_box = load_bounding_box(source)
        data = dict(
            places=scrape_osm(bounding_box),
            osm_scraping_finished=current_time_str(),
            bounding_box=bounding_box,
        )
    else:
        # get places from osm file
        with open(source, 'r') as f:
            data = json.load(f)

    if use_google:
        data['places'] = scrape_google(data['places'])
        data['google_scraping_finished'] = current_time_str()

    with open(target, 'w') as f:
        json.dump(data)


def main():
    args = parse_args(sys.argv[1:])

    # if neither --osm nor --google is set, both are used
    use_osm, use_google = args.osm, args.google
    if not use_osm and not use_google:
        use_osm, use_google = True, True

    # set proxy with host and port
    try:
        proxy_hpst, proxy_port = parse_proxy(args)
    except ValueError:
        print ("Proxy needs to be in format <host>:<port>.")
        quit()

    if (proxy_hpst and proxy_port) is not None:
        init_proxy(proxy_hpst, proxy_port)

    # check if conneciton is available
    if not test_connection():
        quit()

    # check if input is directory or file
    if not os.path.exists(args.source_path):
        print ("Source path '{}' does not exist".format(args.source_path))
        return False

    if os.path.isdir(args.source_path):
        # go through all files in dir
        paths = list()
        for dirname, _, filenames in os.walk(args.source_path):
            for filename in filenames:
                paths.append(os.path.join(dirname, filename))
        with tqdm(paths) as progress_bar:
            for path in progress_bar:
                progress_bar.write("Processing file '{}'.".format(path))
                crawl_file(path, args.target_path, use_osm, use_google)
    else:
        crawl_file(args.source_path, args.target_path, use_osm, use_google)