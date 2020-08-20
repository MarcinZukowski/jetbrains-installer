# JetBrains Installer

A little tool I wrote when I realized how often I install JetBrains
tools on various machines.

## Usage

See all options

    ./jbi.py --help

Example: Download CLion

    ./jbi.py clion linux

Example: Download and install IntelliJ Idea Community in `$HOME/local`, creating a soft link (useful when versions change)

    ./jbi.py ideac linux -i -l -p $HOME/local

Example: Update PyCharm Professional to the latest version, updating the soft link, and creating an application link

    ./jbi.py pycharmp linux -i -l -a -p $HOME/local -f

Example: Install latest Intellij-Ultimate EAP to `/opt` (default - requires write permission for current user), creating an application link

    ./jbi.py ideaU linux --install --link --app --prefix=/opt --channel=eap

Example: See possible platforms for IntelliJ Idea Community

    ./jbi.py ideac


## CLI shortcut shim

To add a CLI shim (e.g. `idea`) that doesn't hang around in terminal, run the following, adjusting paths as needed:

```bash
echo '/opt/idea/bin/idea.sh "$@" </dev/null &>/dev/null & disown $!' | sudo tee /usr/local/bin/idea
sudo chmod +x /usr/local/bin/idea
```

Now try open a directory as a project:

    cd ~/workspace/
    idea .


> FYI `$!` is a shortcut to the PID of the last background job
>
> Stdout & stderr are piped to `/dev/null`, so something like `idea --help` won't return anything, use `idea.sh` directly
  for that use case.


## MacOSX notes

The installation currently always installs under /Applications.
If the application with the same name existed, it will rename it to .old.

## Windows notes

* Not tested at all `:)`

