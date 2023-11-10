import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "application.app:app",
        port=8080,
        # host="0.0.0.0",
        # reload=True,
        # reload_dirs=["./application", "./data", "./authentication"],
    )
