FROM freqtradeorg/freqtrade@sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db

USER root
RUN mkdir -p /freqtrade/user_data/logs && chown -R ftuser:ftuser /freqtrade/user_data
COPY --chown=ftuser:ftuser config/paper.json /opt/btc/config/paper.json
COPY --chown=ftuser:ftuser strategies/DynamicBtc.py /opt/btc/strategies/DynamicBtc.py
USER ftuser

LABEL org.opencontainers.image.source="https://github.com/JensdeVlaming/freqtrade"
LABEL org.opencontainers.image.description="Frozen V5 BTC spot strategy for forward paper trading"
