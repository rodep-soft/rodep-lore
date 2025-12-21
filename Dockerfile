FROM python:3.11-slim

WORKDIR /docs

RUN pip install --no-cache-dir \
  sphinx \
  sphinx-autobuild \
  myst-parser \
  furo

CMD ["bash"]
