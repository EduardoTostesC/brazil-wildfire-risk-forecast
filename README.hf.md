---
title: Brazil Wildfire Risk Forecast
emoji: 🔥
colorFrom: red
colorTo: orange
sdk: docker
app_port: 8501
pinned: false
license: mit
short_description: Historical satellite hotspot risk replay in Mato Grosso
---

# Historical hotspot risk replay

Retrospective Portuguese/English demonstration using exact archived observations. Operational forecasting is unavailable. Metrics and limitations are maintained in the [publication branch documentation](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/tree/release/retrospective-publication-2026-10-26).

The prepared export from scripts/prepare_space.py uses Dockerfile.serving and starts Streamlit on port 8501 with only runtime dependencies. No full raw dataset or credentials are included. Review docs/DEPLOY_RETROSPECTIVO.md and the platform's current account requirements before uploading. This file is a template, not evidence of a live Space.
