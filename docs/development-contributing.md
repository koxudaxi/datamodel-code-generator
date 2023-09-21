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

## 2. Install [poetry](https://github.com/python-poetry/poetry)
$ curl -sSL https://install.python-poetry.org | python3 - 

## 3. Install dependencies
$ poetry install

## 4. Create new branch and rewrite code.
$ git checkout -b new-branch

## 5. Run unittest (you should pass all test and coverage should be 100%)
$ poetry run ./scripts/test.sh

## 6. Format code
$ poetry run ./scripts/format.sh

## 7. Check lint (mypy)
$ poetry run ./scripts/lint.sh

## 8. Commit and Push...
```
