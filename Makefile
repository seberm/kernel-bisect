.PHONY: clean

all: 

clean:
	rm -rvf .tox dist kernel_bcontrol.egg-info
	-find . -type f -name "*.pyc" -exec rm -vf {} \;
	-find . -type d -name "__pycache__" -exec rm -rvf {} \;
