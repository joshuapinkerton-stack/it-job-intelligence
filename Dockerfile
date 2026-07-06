FROM apify/actor-python:3.14

COPY --chown=apify:apify requirements.txt ./
RUN pip install -r requirements.txt && pip freeze

COPY --chown=apify:apify . ./

RUN python -m compileall -q it_job_intelligence/

CMD ["python", "-m", "it_job_intelligence"]
