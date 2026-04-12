# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

FROM python:3.13-slim-bookworm

ADD . /rockchip_stats

WORKDIR /rockchip_stats

RUN python3 -m pip install --upgrade pip && \
    pip3 install -v .

CMD ["rtop"]
