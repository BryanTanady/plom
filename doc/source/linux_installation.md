<!--
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2023 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2019-2020 Matthew Coles"
__license__ = "AGPL-3.0-or-later"
 -->

Installing from source on GNU/Linux
===================================

For production use of Plom we recommend using Docker.  These instructions below
are mainly for developers, packagers, etc.
If you only want to grade some papers, then you don't need any of this; instead
go to [plomgrading.org](https://plomgrading.org) and follow instructions for getting started with
a **Plom Client**.


Fedora
------

Tested on Fedora 37.  Some stuff from the package manager:
```
  # sudo dnf install \
        ImageMagick openssl gcc gcc-c++ cmake \
        turbojpeg-devel libjpeg-turbo-devel python3-cffi \
        python3-passlib python3-qt5 \
        python3-jsmin python3-defusedxml python3-yaml \
        python3-more-itertools python3-chardet \
        python3-seaborn python3-cairosvg \
        python3-aiohttp python3-appdirs python3-arrow \
        python3-pillow python3-pandas python3-peewee \
        python3-PyMuPDF python3-scikit-learn \
        python3-stdiomask python3-requests-toolbelt \
        python3-pip python3-wheel python3-setuptools \
        python3-tomlkit python3-tqdm python3-urllib3 \
        python3-pytest python3-PyMySQL \
        latexmk tex-dvipng texlive-scheme-basic \
        tex-preview tex-charter tex-exam tex-preprint \
        python3-myst-parser python3-sphinx python3-sphinx_rtd_theme \
        python3-sphinx-argparse
```
At this point `pip install plom` (or `pip install --user .` from inside
the Plom source tree) should pull in the remaining dependencies.
There are additional dependencies for the machine-learning-based ID Reader:
```
  # pip install --user imutils lapsolver opencv-python-headless
```
If you're building a production server you may want to ignore some of the above
and instead use pinned versions:
```
  # pip install --user -r requirements.txt
```
You may also want to consider a tool like `virtualenv`.


Ubuntu
------

Plom requires Python 3.7, perhaps it will soon require 3.8.
It will not work on Ubuntu 18.04.  It is time to upgrade your OS.

Some stuff from the package manager:
```
  # sudo apt install \
        cmake make imagemagick dvipng g++ openssl \
        libjpeg-turbo8-dev libturbojpeg0-dev \
        python3-passlib python3-pandas python3-pyqt5 python3-pytest \
        python3-dev python3-pip python3-setuptools python3-wheel \
        python3-requests-toolbelt texlive-latex-extra \
        latexmk texlive-fonts-recommended python3-pillow \
        python3-tqdm libpango-1.0-0 libpangocairo-1.0-0 \
        python3-defusedxml python3-jsmin python3-cairosvg
```
The `pango` stuff was needed for `weasyprint`: perhaps it can be dropped (?)
The `libjpeg` stuff can likely be dropped too (?)

Now upgrade pip (your local copy, not the system one)
```
  # pip3 install --upgrade --user pip
  # python3 -m pip install --upgrade --user setuptools
  # python3 -m pip --version
  # pip3 --version
  # pip --version
```
Note `python3 -m pip` is some kind of workaround for old OSes.
On Ubuntu 20.04, you should be able to just use "pip", but inspect output to be sure.
Similarly, on new enough systems, you don't need to pip install a new `setuptools`.

At this point `pip install --user .` from inside the Plom source tree should pull
in the remaining dependencies.

If you're building a production server you may want to ignore some of the above
and instead use pinned versions:
```
  # python3 -m pip install --user -r requirements.txt
```
You may also want to consider a tool like `virtualenv`.

Another thing to watch out for (at least on Ubuntu 18.04) is that
`pip install --user ...` commands will install binaries in
`${HOME}/.local/bin` but this is not in your `$PATH` by default.
You may need to update your path in a file such as `.bashrc`.
