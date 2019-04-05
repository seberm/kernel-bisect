# Kernel Git Bisect automation

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

