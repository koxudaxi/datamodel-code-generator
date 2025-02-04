# Development

Install the package in editable mode:

```sh
$ git clone git@github.com:koxudaxi/datamodel-code-generator.git
$ pip install -e datamodel-code-generator
```

# Contribute

We are waiting for your contributions to `datamodel-code-generator`.

## How to contribute

```bash
## 1. Clone your fork repository
$ git clone git@github.com:<your username>/datamodel-code-generator.git
$ cd datamodel-code-generator

## 2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
$ curl -LsSf https://astral.sh/uv/install.sh | sh

## 3. Install tox with uv
$ uv tool install --python-preference only-managed --python 3.13 tox --with tox-uv

## 3. Create developer environment
$ tox run -e dev

.tox/dev is a Python environment you can use for development purposes

## 4. Create new branch and rewrite code.
$ git checkout -b new-branch
 
## 5. Run unittest under Python 3.13 (you should pass all test and coverage should be 100%)
$ tox run -e 3.13

## 7. Format and lint code (will print errors that cannot be automatically fixed)
$ tox run -e fix

## 8. Commit and Push...
```
