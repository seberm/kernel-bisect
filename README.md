# Kernel Git Bisect automation


## Installation

### Installation of dependencies

#### Fedora
```
sudo dnf install python3-click ansible git
```

#### pip
```
$ pip install -r requirements.txt
$ python setup.py install
```

### Run this project
Clone project
```
$ git clone https://gitlab.com/seberm/kernel-bisect.git
$ cd kernel-bisect
```

Create ansible inventory
```
$ cat > remotes.txt <<EOF
[all:vars]
ansible_connection=ssh
ansible_user=root
ansible_ssh_pass=toor

[duts]
host1.example.com
host2.example.com

[duts-mgmt]
host1-mgmt.example.com
host2-mgmt.example.com
EOF
```

Try to run:
```
$ bcontrol.py --version
```

## Basic usage
Check connection and dependencies:
```
$ bcontrol.py ping
```

Bcontrol tool supports the dry-run:
```
$ bcontrol.py --dry-run ping
```

Basic information about kernel on all DUTs:
```
$ bcontrol.py uname -- --all
```

Run specified command on all DUTs:
```
$ bcontrol.py sh ls -- -alh
```

Reboot all DUTs machines:
```
$ bcontrol.py reboot
```

Run script.sh in all DUTs and return the output:
```
$ bcontrol.py run script.sh
```

Build kernel and genrate binary RPM package:
```
$ bcontrol.py build --jobs 4 -C ~/repos/linux-torvalds-repository
```

Try to install specified kernel on all DUTs and reboot into it:
```
$ bcontrol.py kernel-install --from-rpm /tmp/rpmbuild-kernel-bisect/RPMS/x86_64/kernel-5.1.0_rc3+-5.x86_64.rpm
```

## How to use bcontrol with git-bisect

Usage from git-bisect:
```
$ cd ~/repos/kernel-tree
$ git bisect run bcontrol bisect from-git test-script.sh
```

Possibility to run git-bisect using bcontrol (git-bisect runs as a subprocess):
```
$ cd kernel-tree
$ bcontrol bisect -C ~/repos/kernel-tree run test-script.sh
```

## Support

### Supported distros
* RHEL == 7
* CentOS >= 7
* Fedora >= 27

## Dependencies

### Client
* python >= 3.6
* Click
* ansible
* git

And everything ansible modules need, e.g.:
* ipmi\_power: pyghmi

### Server(s)
* SSH daemon running
* Everything the Ansible and Ansible modules need (e.g. python)

## TODOs
* When logging mode is set to debug, run all ansible commands with -vvv option.
* Integrate bcontrol into global/local git config.
* GitHub will be mirror
* Create wrapper for git-bisect run to have possibility to run bisect from git directly
* Also support wrapper around git-bisect, to have possibility to run git-bisect run from bcontrol
* Use terminalizer to record usage GIF

## Authors
* Otto Sabart <seberm@seberm.com>

