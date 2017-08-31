#!/usr/bin/env python

import json
import shutil
import sys
import optparse
import os.path
import tarfile
import urllib

DEFAULT_PREFIX = "/opt"
DEFAULT_TMPDIR = "/tmp"
APP_PREFIX = os.path.expanduser('~/.local/share/applications')


class Tool:
    """Defines a single IntelliJ tool"""
    def __init__(self, name, code, binname, aliases=None):
        self.name = name
        self.code = code
        self.binname = binname
        self.aliases = aliases if aliases else []
        self.aliases.append(self.code)

tools = [
    Tool("CLion", "CL", "clion"),
    Tool("IntelliJ-Ultimate", "IIU", "idea", ["ideaU"]),
    Tool("IntelliJ-Community", "IIC", "idea", ["ideaC"]),
    Tool("PyCharm-Professional", "PCP", "pycharm", ["pycharmP"]),
    Tool("PyCharm-Community", "PCC", "pycharm", ["pycharmC"]),
    Tool("WebStorm", "WS", "webstorm"),
    Tool("DataGrip", "DG", "datagrip"),
    Tool("PhpStorm", "PH", "phpstorm")
]

toolMap = {}

for t in tools:
    toolMap[t.name.lower()] = t
    for a in t.aliases:
        toolMap[a.lower()] = t


def error(msg):
    global parser
    print "ERROR: {0}".format(msg)
    parser.print_help()
    sys.exit(1)


def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def platforms(data):
    return "Available platforms:\n  {0}".format("\n  ".join(data["downloads"].keys()))


class MyParser(optparse.OptionParser):
    def format_epilog(self, formatter):
        res = "Available products: "
        for t in tools:
            res += "\n  {0:25s} aliases: {1}".format(t.name, " ".join(t.aliases))
        return res


def do_download(download):
    global tool, tmpdir

    link = download["link"]
    fname = link.split('/')[-1]
    size = download["size"]

    print "Found {product} version {version}, file: {fname} ({size}) bytes".format(
        product=tool.name, version=version, fname=fname, size=size)

    # TODO: make it work with https
    link = link.replace("https", "http")

    mkdirs(tmpdir)
    fname = os.path.join(tmpdir, fname)

    ready = False
    if os.path.isfile(fname):
        fsize = os.path.getsize(fname)
        # TODO: add checksum check
        if fsize != size:
            print "File exists, but the size differs ({0} vs {1}), downloading again".format(fsize, size)
        else:
            print "File exists and size matches, skipping downloading"
            ready = True

    if not ready:
        print "Downloading from {0} to {1}".format(link, fname)
        urllib.urlretrieve(link, fname, reporthook=progress)

        progress(1, size, size)
        print "\nDone!"

    return fname


def progress(a, b, c):
    """Function that prints download progress"""
    sofar = a * b
    if a % 100 == 1:
        sys.stdout.write("\r{0} / {1} bytes loaded ({2:05.2f}%)".format(sofar, c, 100.0 * sofar / c))
        sys.stdout.flush()


parser = MyParser(usage='Usage: %prog [options] <product> <platform>',
                  description="Install various JetBrains tools")
parser.add_option("-f", "--force", help="Force download and installation, even if the file exists", action="store_true")
parser.add_option("-i", "--install", help="Install after downloading", action="store_true")
parser.add_option("-l", "--link", help="Create a softlink with base product name", action="store_true")
parser.add_option("-p", "--prefix", help="Directory to install the tool (default={0})".format(DEFAULT_PREFIX))
parser.add_option("-t", "--tmpdir", help="Temporary directory for downloaded files(default={0})".format(DEFAULT_TMPDIR))
parser.add_option("-a", "--app", help="Add application to ~/.local/share/applications", action="store_true")

(options, args) = parser.parse_args()
prefix = options.prefix if options.prefix else DEFAULT_PREFIX
tmpdir = options.tmpdir if options.tmpdir else DEFAULT_TMPDIR

if len(args) > 2:
    error("Too many arguments.")

if len(args) == 0:
    error("Need to provide a product.")

product = args[0]

tool = toolMap.get(product.lower())

if not tool:
    error("Unknown product: {0}".format(product))

print "Downloading {0}".format(tool.name)

code = tool.code

releases_link = "http://data.services.jetbrains.com/products/releases?code={0}&latest=true&type=release".format(code)

f = urllib.urlopen(releases_link)
resp = json.load(f)
data = resp[code][0]

if len(args) == 1:
    print "No platform provided."
    print platforms(data)
    sys.exit(1)

platform = args[1]

download = data["downloads"].get(platform)

if not download:
    print "Unknown platform: {0}".format(platform)
    print platforms(data)
    sys.exit(1)

version = data["version"]

fname = do_download(download)

if options.install:
    # Determine the name of the output directory
    tar = tarfile.open(fname)
    first = tar.next()
    dir = first.name
    while True:
        if os.path.dirname(dir) == "":
            dir = os.path.basename(dir)
            break
        dir = os.path.dirname(dir)

    mkdirs(prefix)
    fulldir = os.path.join(prefix, dir)

    if os.path.exists(fulldir):
        print "Target directory {0} already exists".format(fulldir)
        if options.force:
            print "Deleting {0}".format(fulldir)
            shutil.rmtree(fulldir)
        else:
            print "Stopping. Use --force to delete old installation"
            exit(1)

    print "Extracting into {0}".format(fulldir)
    tar.extractall(prefix)

    if options.link:
        linkname = os.path.join(prefix, dir.split('-')[0])
        if os.path.exists(linkname):
            print "Deleting old link {0}".format(linkname)
            os.remove(linkname)
        print "Linking {0} to {1}".format(dir, linkname)
        os.symlink(dir, linkname)

        fulldir = linkname

    if options.app:
        app_dir = APP_PREFIX
        mkdirs(app_dir)
        app_path = os.path.join(app_dir, tool.name + ".desktop")
        print "Creating {0}".format(app_path)

        with open(app_path, "w") as f:
            f.write("""
[Desktop Entry]
Name={name}
Exec={binname}
StartupNotify=true
Terminal=false
Type=Application
Categories=Development;IDE;
Icon={icon}""".format(
                name=tool.name,
                binname=os.path.join(fulldir, "bin", tool.binname + ".sh"),
                icon=os.path.join(fulldir, "bin", tool.binname + ".png")))

