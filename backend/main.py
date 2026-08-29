from daytona import Daytona, DaytonaConfig
import os

config = DaytonaConfig(api_key=os.getenv("DAYTONA_API_KEY"))

daytona = Daytona(config)

sandbox = daytona.create()

response = sandbox.process.code_run('print("Hello World from code!")')
if response.exit_code != 0:
    print(f"Error: {response.exit_code} {response.result}")
else:
    print(response.result)