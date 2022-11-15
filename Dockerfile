ARG BASE_CR
FROM $BASE_CR/analysis-runner/images/driver:latest

COPY README.md .
COPY setup.py .
COPY cpg_utils cpg_utils
RUN pip install .
