name: Release Docker Image

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      docker_tag:
        description: 'Docker tag to use (ex. v1.0.0)'
        required: true
        type: string

jobs:
  release-docker-image:
    runs-on: code-linux
    steps:
      - uses: SamsungHumanoid/container-runner/actions/release_docker_image@main
        with:
          bart_repo: samsung-humanoid-docker-local.bart.sec.samsung.net
          github_srbot_password: ${{ secrets.SRBOT_GITHUB_CICD }}
          bart_srbot_password: ${{ secrets.SRBOT_BART_CICD }}
          docker_tag: ${{ format('{0}-{1}', inputs.docker_tag || github.ref_name, github.sha) }}
          container_runner_repo: "SamsungHumanoid/container-runner"
