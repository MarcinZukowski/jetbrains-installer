#!/usr/bin/env python3

import glob
import json
import optparse
import os
import os.path
import stat
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_RELEASE = None
DEFAULT_CHANNEL = "release"
KNOWN_CHANNELS = ["release", "rc"]
DEFAULT_PREFIX = "/opt"
DEFAULT_TMPDIR = "/tmp"
APP_PREFIX = os.path.expanduser('~/.local/share/applications')
DESKTOP_PREFIX = os.path.expanduser('~/Desktop')


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
    Tool("PhpStorm", "PH", "phpstorm"),
    Tool("Rider", "RD", "rider")
]

toolMap = {}

for t in tools:
    toolMap[t.name.lower()] = t
    for alias in t.aliases:
        toolMap[alias.lower()] = t


def error(msg):
    print("ERROR: {0}".format(msg))
    sys.exit(1)


def usage(msg):
    global parser
    print("ERROR: {0}".format(msg))
    parser.print_help()
    sys.exit(1)


def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def shell(cmd, stderr=None):
    print("Running: {0}".format(cmd))
    return subprocess.check_output(cmd, shell=True, universal_newlines=True, stderr=stderr)


def platforms(data):
    return "Available platforms:\n  {0}".format("\n  ".join(data["downloads"].keys()))


class MyParser(optparse.OptionParser):
    def format_epilog(self, formatter):
        res = "Available products: "
        for t in tools:
            res += "\n  {0:25s} aliases: {1}".format(t.name, " ".join(t.aliases))
        return res


def get_tool_data(tool):
    global channel, release
    code = tool.code

    print("Determining the version for {0} from channel {1}".format(code, channel))

    releases_link = "http://data.services.jetbrains.com/products/releases?code={0}&latest={2}&type={1}".format(
        code, channel, "true" if release is None else "false")

    f = urllib.request.urlopen(releases_link)
    resp = json.load(f)
    if release is None:
        return resp[code][0]
    else:
        # Find the release
        for rel in resp[code]:
            build = rel["build"]
            version = rel["version"]
            majorVersion = rel["majorVersion"]
            year = majorVersion.split(".")[0]
            if release in (build, version, majorVersion, year):
                return rel
    error("Can not find release {0} for tool {1} in channel {2}".format(release, code, channel))


def do_download(download):
    global tool, tmpdir

    link = download["link"]
    fname = link.split('/')[-1]
    size = download["size"]

    print("Found {product} version {version}, file: {fname} ({size}) bytes".format(
        product=tool.name, version=version, fname=fname, size=size))

    # TODO: make it work with https
    link = link.replace("https", "http")

    mkdirs(tmpdir)
    fname = os.path.join(tmpdir, fname)

    ready = False
    if os.path.isfile(fname):
        fsize = os.path.getsize(fname)
        # TODO: add checksum check
        if fsize != size:
            print("File exists, but the size differs ({0} vs {1}), downloading again".format(fsize, size))
        else:
            print("File exists and size matches, skipping downloading")
            ready = True

    if not ready:
        print("Downloading from {0} to {1}".format(link, fname))
        urllib.request.urlretrieve(link, fname, reporthook=progress)

        progress(1, size, size)
        print("\nDone!")

    return fname


def do_install_linux(fname):
    # Determine the name of the output directory
    print("Opening file: {}".format(fname))
    tar = tarfile.open(fname)
    first = tar.next()
    dirname = first.name
    while True:
        if os.path.dirname(dirname) == "":
            dirname = os.path.basename(dirname)
            break
        dirname = os.path.dirname(dirname)

    mkdirs(prefix)
    fulldir = os.path.join(prefix, dirname)

    do_extract = True
    if os.path.exists(fulldir):
        print("Target directory {0} already exists".format(fulldir))
        if options.force:
            print("Deleting {0}".format(fulldir))
            shutil.rmtree(fulldir)
        else:
            print("Not installing the tool. Use --force to delete old installation")
            do_extract = False
            
    if do_extract:
        print("Extracting into {0}".format(fulldir))
        tar.extractall(prefix)

    if options.link:
        linkname = os.path.join(prefix, dirname.split('-')[0])
        if os.path.exists(linkname):
            print("Deleting old link {0}".format(linkname))
            os.remove(linkname)
        print("Linking {0} to {1}".format(dirname, linkname))
        os.symlink(dirname, linkname)

        fulldir = linkname

    desktop_entry = """
[Desktop Entry]
Name={name}
Exec={binname}
StartupNotify=true
Terminal=false
Type=Application
Categories=Development;IDE;
Icon={icon}""".format(
                name=tool.name,
                binname=os.path.join(fulldir, "bin", tool.binname + ".sh").replace(" ", "\\ "),
                icon=os.path.join(fulldir, "bin", tool.binname + ".png"))

    if options.app:
        mkdirs(APP_PREFIX)
        app_path = os.path.join(APP_PREFIX, tool.name + ".desktop")
        print("Creating {0}".format(app_path))

        with open(app_path, "w") as f:
            f.write(desktop_entry)
            
    if options.desktop:
        mkdirs(DESKTOP_PREFIX)
        app_path = os.path.join(DESKTOP_PREFIX, tool.name + ".desktop")
        print("Creating {0}".format(app_path))

        with open(app_path, "w") as f:
            f.write(desktop_entry)
            
        # Add +x
        st = os.stat(app_path)
        os.chmod(app_path, st.st_mode | stat.S_IEXEC)


def do_install_macosx(fname):
    print("Mounting {}".format(fname))
    out = shell("hdiutil attach -readonly '{0}'".format(fname, sys.stdout))
    mnt = re.split(r" [ ]+", out.splitlines()[-1])[2].strip()
    print("Mounted as {}".format(mnt))
    fullapps = glob.glob(os.path.join(mnt, "*.app"))
    if len(fullapps) != 1:
        error("Expect exactly 1 .app in the mounted directory")
    fullapp = fullapps[0]
    app = os.path.split(fullapp)[-1]
    app_install_path = os.path.join("/Applications", app)
    if os.path.exists(app_install_path):
        old_path = app_install_path + ".old"
        if os.path.exists(old_path):
            print("WARNING: deleting {0}".format(old_path))
            shell("rm -rf '{0}'".format(old_path))
        print("WARNING:\n  {0}\nexists, renaming to\n  {1}".format(app_install_path, old_path))
        os.rename(app_install_path, old_path)
    print("Copying to {0}".format(app_install_path))
    shell("cp -R '{0}' '{1}'".format(fullapp, app_install_path))
    if os.path.exists(app_install_path):
        "Application installed in {0}".format(app_install_path)
    else:
        error("Unexpected error when installing the app")
    shell("hdiutil detach '{0}'".format(mnt))


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
parser.add_option("-c", "--channel", help="Channell to use(default={0}, accepted values: {1})".format(
    DEFAULT_CHANNEL, ", ".join(KNOWN_CHANNELS)))
parser.add_option("-a", "--app", help="Add application to ~/.local/share/applications", action="store_true")
parser.add_option("-d", "--desktop", help="Add application to ~/Desktop", action="store_true")
parser.add_option("-r", "--release", help="""Determine the exact tool release. Can be one of:
year (e.g. "2019"), major version (e.g. "2019.3"), minor version ("2019.3.4"), or build number (e.g. "193.6911.18").
(default,empty=latest)""")

(options, args) = parser.parse_args()
prefix = options.prefix if options.prefix else DEFAULT_PREFIX
tmpdir = options.tmpdir if options.tmpdir else DEFAULT_TMPDIR

channel = options.channel if options.channel else DEFAULT_CHANNEL
if channel not in KNOWN_CHANNELS:
    usage("Unknown channel: {0}, accepted values: {1}".format(channel, ", ".join(KNOWN_CHANNELS)))

release = options.release or DEFAULT_RELEASE
if release == "latest" or release == "":
  release = None

if len(args) > 2:
    usage("Too many arguments.")

if len(args) == 0:
    usage("Need to provide a product.")

product = args[0]

tool = toolMap.get(product.lower())

if not tool:
    usage("Unknown product: {0}".format(product))

print("Downloading {0}".format(tool.name))

tool_data = get_tool_data(tool)

if len(args) == 1:
    print("No platform provided.")
    print(platforms(tool_data))
    sys.exit(1)

platform = args[1]

download_data = tool_data["downloads"].get(platform)

if not download_data:
    print("Unknown platform: {0}".format(platform))
    print(platforms(tool_data))
    sys.exit(1)

version = tool_data["version"]

downloaded_fname = do_download(download_data)

if options.install:
    if sys.platform in ("linux", "linux2"):
        do_install_linux(downloaded_fname)
    elif sys.platform == "darwin":
        do_install_macosx(downloaded_fname)
    else:
        ("Unsupported platform for installation: {}".format(sys.platform))
