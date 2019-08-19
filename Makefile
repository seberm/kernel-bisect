.PHONY: clean

all: 

clean:
	rm -rf .tox
	-find . -type f -name "*.pyc" -exec rm -f {} \;
	-find . -type d -name "__pycache__" -exec rm -rf {} \;
