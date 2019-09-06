# WizFi630S Test Tool

## Virtual environment

```
pip install virtualenv
virtualenv .venv
```

* Windows

  ```
  call .venv\Scripts\activate
  ```

* Linux

  ```
  source .venv/bin/activate
  ```

## Package Install

```
pip install -r requirements.txt
```

## Run

```
python src/main/python/main.py
```

----

## Using fbs

```bash
# run
fbs run

# freeze
fbs freeze
```
----

## Using pyinstaller


```bash
# Modify main.py: set USE_PYINSTALLER to True
USE_PYINSTALLER = True

# Make excutable file
cd src/main/python
pyinstaller setup_exe.spec
```

