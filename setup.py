#!/usr/bin/env python3

from setuptools import setup

#with open("README.md", "r", encoding="utf-8") as f:
#    readme = f.read()

setup(
    name="kernel-bcontrol",
    #version=versioneer.get_version(),
    version="v0.0.1",

    # FIXME: Unfortunately this does not work with setuptools (bdist_rpm
    #        subcommand)
    #cmdclasy=versioneer.get_cmdclass(),
    description="Automation of kernel git bisection.",
    #long_description=readme,
    author="Otto Sabart",
    author_email="seberm@seberm.com",
    url="https://github.com/seberm/kernel-bisect",
    keywords=[],
    include_package_data=True,
    packages=[
        "bcontroller",
    ],
    entry_points={
        "console_scripts": [
            "kernel-bcontrol = bcontrol.__main__:cli",
        ]
    },
    options={
        "build_scripts": {
            # This is because of RHEL-7. The default python3 is v3.4, but we build packages for python3.6 (fedora). This fixes shebang in entry-points.
            #'executable': '/usr/bin/env python3',
        }
    },
    classifiers=[
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    install_requires=[
        "Click",
        "ansible",
    ],
)
