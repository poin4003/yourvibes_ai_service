# Name app
APP_NAME = main.py

# Config by OS
ifeq ($(OS),Windows_NT)
	SET_ENV = set
else
	SET_ENV = export
endif

# Config command
dev:
	@echo "Running in development mode"
	@$(SET_ENV) YOURVIBES_AI_CONFIG_FILE=dev&&python ./src/$(APP_NAME)

prod:
	@echo "Running in production mode"
	@$(SET_ENV) YOURVIBES_AI_CONFIG_FILE=prod&&python ./src/$(APP_NAME)