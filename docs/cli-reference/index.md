# 🖥️ CLI Reference

This documentation is auto-generated from test cases.

🔍 **[Quick Reference](quick-reference.md)** - All options on one page for Ctrl+F search

## 📂 Categories

| Category | Options | Description |
|----------|---------|-------------|
| 📁 [Base Options](base-options.md) | 5 | Input/output configuration |
| 🔧 [Typing Customization](typing-customization.md) | 17 | Type annotation and import behavior |
| 🏷️ [Field Customization](field-customization.md) | 20 | Field naming and docstring behavior |
| 🏗️ [Model Customization](model-customization.md) | 27 | Model generation behavior |
| 🎨 [Template Customization](template-customization.md) | 16 | Output formatting and custom rendering |
| 📘 [OpenAPI-only Options](openapi-only-options.md) | 6 | OpenAPI-specific features |
| ⚙️ [General Options](general-options.md) | 14 | Utilities and meta options |
| 📝 [Utility Options](utility-options.md) | 5 | Help, version, debug options |

## All Options

**Jump to:** [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [K](#k) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w)


### A {#a}

- [`--additional-imports`](template-customization.md#additional-imports)
- [`--aliases`](field-customization.md#aliases)
- [`--all-exports-collision-strategy`](general-options.md#all-exports-collision-strategy)
- [`--all-exports-scope`](general-options.md#all-exports-scope)
- [`--allof-merge-mode`](typing-customization.md#allof-merge-mode)
- [`--allow-extra-fields`](model-customization.md#allow-extra-fields)
- [`--allow-population-by-field-name`](model-customization.md#allow-population-by-field-name)

### B {#b}

- [`--base-class`](model-customization.md#base-class)

### C {#c}

- [`--capitalize-enum-members`](field-customization.md#capitalize-enum-members)
- [`--check`](general-options.md#check)
- [`--class-name`](model-customization.md#class-name)
- [`--collapse-root-models`](model-customization.md#collapse-root-models)
- [`--custom-file-header`](template-customization.md#custom-file-header)
- [`--custom-file-header-path`](template-customization.md#custom-file-header-path)
- [`--custom-formatters`](template-customization.md#custom-formatters)
- [`--custom-formatters-kwargs`](template-customization.md#custom-formatters-kwargs)
- [`--custom-template-dir`](template-customization.md#custom-template-dir)

### D {#d}

- [`--dataclass-arguments`](model-customization.md#dataclass-arguments)
- [`--debug`](utility-options.md#debug)
- [`--disable-appending-item-suffix`](template-customization.md#disable-appending-item-suffix)
- [`--disable-future-imports`](typing-customization.md#disable-future-imports)
- [`--disable-timestamp`](template-customization.md#disable-timestamp)
- [`--disable-warnings`](general-options.md#disable-warnings)

### E {#e}

- [`--empty-enum-field-name`](field-customization.md#empty-enum-field-name)
- [`--enable-command-header`](template-customization.md#enable-command-header)
- [`--enable-faux-immutability`](model-customization.md#enable-faux-immutability)
- [`--enable-version-header`](template-customization.md#enable-version-header)
- [`--encoding`](base-options.md#encoding)
- [`--enum-field-as-literal`](typing-customization.md#enum-field-as-literal)
- [`--extra-fields`](field-customization.md#extra-fields)
- [`--extra-template-data`](template-customization.md#extra-template-data)

### F {#f}

- [`--field-constraints`](field-customization.md#field-constraints)
- [`--field-extra-keys`](field-customization.md#field-extra-keys)
- [`--field-extra-keys-without-x-prefix`](field-customization.md#field-extra-keys-without-x-prefix)
- [`--field-include-all-keys`](field-customization.md#field-include-all-keys)
- [`--force-optional`](model-customization.md#force-optional)
- [`--formatters`](template-customization.md#formatters)
- [`--frozen-dataclasses`](model-customization.md#frozen-dataclasses)

### G {#g}

- [`--generate-cli-command`](general-options.md#generate-cli-command)
- [`--generate-pyproject-config`](general-options.md#generate-pyproject-config)

### H {#h}

- [`--help`](utility-options.md#help)
- [`--http-headers`](general-options.md#http-headers)
- [`--http-ignore-tls`](general-options.md#http-ignore-tls)
- [`--http-query-parameters`](general-options.md#http-query-parameters)

### I {#i}

- [`--ignore-enum-constraints`](typing-customization.md#ignore-enum-constraints)
- [`--ignore-pyproject`](general-options.md#ignore-pyproject)
- [`--include-path-parameters`](openapi-only-options.md#include-path-parameters)
- [`--input`](base-options.md#input)
- [`--input-file-type`](base-options.md#input-file-type)

### K {#k}

- [`--keep-model-order`](model-customization.md#keep-model-order)
- [`--keyword-only`](model-customization.md#keyword-only)

### M {#m}

- [`--module-split-mode`](general-options.md#module-split-mode)

### N {#n}

- [`--no-alias`](field-customization.md#no-alias)
- [`--no-color`](utility-options.md#no-color)
- [`--no-use-specialized-enum`](typing-customization.md#no-use-specialized-enum)
- [`--no-use-standard-collections`](typing-customization.md#no-use-standard-collections)
- [`--no-use-union-operator`](typing-customization.md#no-use-union-operator)

### O {#o}

- [`--openapi-scopes`](openapi-only-options.md#openapi-scopes)
- [`--original-field-name-delimiter`](field-customization.md#original-field-name-delimiter)
- [`--output`](base-options.md#output)
- [`--output-datetime-class`](typing-customization.md#output-datetime-class)
- [`--output-model-type`](model-customization.md#output-model-type)

### P {#p}

- [`--parent-scoped-naming`](model-customization.md#parent-scoped-naming)
- [`--profile`](utility-options.md#profile)

### R {#r}

- [`--read-only-write-only-model-type`](openapi-only-options.md#read-only-write-only-model-type)
- [`--remove-special-field-name-prefix`](field-customization.md#remove-special-field-name-prefix)
- [`--reuse-model`](model-customization.md#reuse-model)
- [`--reuse-scope`](model-customization.md#reuse-scope)

### S {#s}

- [`--set-default-enum-member`](field-customization.md#set-default-enum-member)
- [`--shared-module-name`](general-options.md#shared-module-name)
- [`--skip-root-model`](model-customization.md#skip-root-model)
- [`--snake-case-field`](field-customization.md#snake-case-field)
- [`--special-field-name-prefix`](field-customization.md#special-field-name-prefix)
- [`--strict-nullable`](model-customization.md#strict-nullable)
- [`--strict-types`](typing-customization.md#strict-types)
- [`--strip-default-none`](model-customization.md#strip-default-none)

### T {#t}

- [`--target-python-version`](model-customization.md#target-python-version)
- [`--treat-dot-as-module`](template-customization.md#treat-dot-as-module)
- [`--type-mappings`](typing-customization.md#type-mappings)

### U {#u}

- [`--union-mode`](model-customization.md#union-mode)
- [`--url`](base-options.md#url)
- [`--use-annotated`](typing-customization.md#use-annotated)
- [`--use-attribute-docstrings`](field-customization.md#use-attribute-docstrings)
- [`--use-decimal-for-multiple-of`](typing-customization.md#use-decimal-for-multiple-of)
- [`--use-default`](model-customization.md#use-default)
- [`--use-default-factory-for-optional-nested-models`](model-customization.md#use-default-factory-for-optional-nested-models)
- [`--use-default-kwarg`](model-customization.md#use-default-kwarg)
- [`--use-double-quotes`](template-customization.md#use-double-quotes)
- [`--use-enum-values-in-discriminator`](field-customization.md#use-enum-values-in-discriminator)
- [`--use-exact-imports`](template-customization.md#use-exact-imports)
- [`--use-field-description`](field-customization.md#use-field-description)
- [`--use-frozen-field`](model-customization.md#use-frozen-field)
- [`--use-generic-container-types`](typing-customization.md#use-generic-container-types)
- [`--use-inline-field-description`](field-customization.md#use-inline-field-description)
- [`--use-non-positive-negative-number-constrained-types`](typing-customization.md#use-non-positive-negative-number-constrained-types)
- [`--use-one-literal-as-default`](model-customization.md#use-one-literal-as-default)
- [`--use-operation-id-as-name`](openapi-only-options.md#use-operation-id-as-name)
- [`--use-pendulum`](typing-customization.md#use-pendulum)
- [`--use-schema-description`](field-customization.md#use-schema-description)
- [`--use-serialize-as-any`](model-customization.md#use-serialize-as-any)
- [`--use-status-code-in-response-name`](openapi-only-options.md#use-status-code-in-response-name)
- [`--use-subclass-enum`](model-customization.md#use-subclass-enum)
- [`--use-title-as-name`](field-customization.md#use-title-as-name)
- [`--use-type-alias`](typing-customization.md#use-type-alias)
- [`--use-unique-items-as-set`](typing-customization.md#use-unique-items-as-set)

### V {#v}

- [`--validation`](openapi-only-options.md#validation)
- [`--version`](utility-options.md#version)

### W {#w}

- [`--watch`](general-options.md#watch)
- [`--watch-delay`](general-options.md#watch-delay)
- [`--wrap-string-literal`](template-customization.md#wrap-string-literal)
