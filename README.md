# JetBrains Installer

A little tool I wrote when I realized how often I install JetBrains
tools on various machines.

## Usage

Download an example tool

    ./jbi.py clion linux

Download and install the tool in `$HOME/local`, creating a soft link (useful when versions change)

    ./jbi.py ideac linux -i -p $HOME/local

See possible platforms for a tool

    ./jbi.py ideac

Get help

    ./jbi.py --help
