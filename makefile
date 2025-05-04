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


# gRPC code generation
PROTO_DIR = proto
OUT_DIR = src/grpc_pkg/comment_pb

gen-grpc:
	@echo Generating gRPC code for $(FILE).proto...
	python -m grpc_tools.protoc -I=$(PROTO_DIR) \
		--python_out=$(OUT_DIR) \
		--grpc_python_out=$(OUT_DIR) \
	$(PROTO_DIR)/$(FILE).proto

.PHONY: dev prod gen-grpc