# Kernel Git Bisect automation

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

## Authors
* Otto Sabart

