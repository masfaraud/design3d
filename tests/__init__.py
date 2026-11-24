import matplotlib

# Non-interactive backend: plt.show() in the code under test must not open windows that block the tests
matplotlib.use("Agg")
