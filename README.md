# JetBrains Installer

A little tool I wrote when I realized how often I install JetBrains
tools on various machines.

## Usage

ee all options

    ./jbi.py --help

Example: Download CLion

    ./jbi.py clion linux

Example: Download and install IntelliJ Idea Community in `$HOME/local`, creating a soft link (useful when versions change)

    ./jbi.py ideac linux -i -p $HOME/local

Example: Update PyCharm Professional to the latest version, updating the soft link, and creating an application link

    ./jbi.py pycharmp linux -i -l -a -p $HOME/local -f

Example: See possible platforms for IntelliJ Idea Community

    ./jbi.py ideac

