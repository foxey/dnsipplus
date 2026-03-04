# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `scripts/lint`).
4. Test you contribution.
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [ruff](https://github.com/astral-sh/ruff) to format and lint the code. Run `scripts/lint` to automatically format and check your code.

## Test your code modification

This custom component includes a development environment in a container, easy to launch if you use Visual Studio Code. With this container you will have a standalone Home Assistant instance running with the integration already loaded.

### Development Setup

1. Open the repository in VS Code with the Dev Container extension
2. The container will automatically set up the development environment
3. Run `scripts/develop` to start Home Assistant
4. Access Home Assistant at http://localhost:8123
5. The integration is automatically loaded from `custom_components/dnsipplus`

### Running Tests

```bash
# Run linting and formatting
scripts/lint

# Run tests (if available)
pytest
```

### Making Changes

1. Make your changes to the code
2. Run `scripts/lint` to ensure code style compliance
3. Test your changes in the development Home Assistant instance
4. Commit your changes with clear, descriptive commit messages

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
