
import zmq
import asyncio
import json
import redis
import os
import signal
import uuid
import zmq.asyncio
from django.core.wsgi import get_wsgi_application
import django


# Set the Django settings module environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.local')

# Initialize Django
django.setup()

# Initialize Django application
from asgiref.sync import sync_to_async
from azma_task.server.models import Logg
# Connect to Redis (Assuming Redis is running on localhost:6379)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

@sync_to_async
def create_logg(message):
    return Logg.objects.create(json_recived=message)


async def run_command_stream(command, command_id):
    """Run the command as a subprocess and yield output line by line asynchronously."""
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    redis_client.hset(f"subprocesses:{command_id}", "pid", process.pid)

    try:
        async for line in process.stdout:
            yield line.decode().strip()
    finally:
        await process.wait()
        redis_client.delete(f"subprocesses:{command_id}")


def stop_subprocess(command_id):
    """Stop the subprocess with the given command_id."""
    pid = redis_client.hget(f"subprocesses:{command_id}", "pid")
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
            redis_client.delete(f"subprocesses:{command_id}")
            return True
        except ProcessLookupError:
            return False
    return False


async def run_command_in_background(command, command_id, socket):
    """Run the command in background, sending its output to the socket."""
    async for line in run_command_stream(command, command_id):
        try:
            print(f"Sending output: {line}")
            await socket.send_string(json.dumps({"command_id": command_id, "output": line}))
        except zmq.ZMQError as e:
            print(f"Error sending data: {e}")
            break

    await socket.send_string("STREAM_END")
    print("Command execution complete.")


async def handle_math_command(data, socket):
    """Handle math commands by evaluating expressions."""
    expression = data["command"].replace("MATH:", "", 1) + " " + " ".join(data.get("parameters", []))
    command_id = data.get("command_id", str(uuid.uuid4()))

    try:
        result = eval(expression)
        await socket.send_string(json.dumps({"command_id": command_id, "result": result}))
    except Exception as e:
        await socket.send_string(f"ERROR: {str(e)}")


async def handle_stop_command(data, socket):
    """Handle STOP commands by terminating a process."""
    command_id = data.get("command_id")
    if not command_id:
        await socket.send_string("ERROR: Command ID is required to stop a process.")
        return

    if stop_subprocess(command_id):
        await socket.send_string(f"Subprocess {command_id} stopped.")
    else:
        await socket.send_string(f"ERROR: Subprocess {command_id} not found.")


async def handle_os_command(data, socket):
    """Handle OS commands by executing them in a subprocess."""
    command = data["command"]
    parameters = data.get("parameters", [])
    command_id = data.get("command_id", str(uuid.uuid4()))
    full_command = f"{command} {' '.join(parameters)}"

    await socket.send_string("STREAM_START")
    await run_command_in_background(full_command, command_id, socket)


async def backend_server():
    """Backend server handling incoming commands and routing them to appropriate handlers."""
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.PAIR)
    socket.bind("tcp://*:5556")

    print("Backend server is running...")

    command_handlers = {
        "MATH": handle_math_command,
        "STOP": handle_stop_command,
    }

    while True:
        try:
            message = await socket.recv_string()
            print(f"Received message: {message}")
            if not message:
                print("Received empty message.")
                continue

            data = json.loads(message)
            command = data.get("command")

            if not command:
                await socket.send_string("ERROR: Command not provided.")
                continue

            await create_logg(message)

            # Route the command to the appropriate handler
            for key, handler in command_handlers.items():
                if command.startswith(key):
                    await handler(data, socket)
                    break
            else:
                # Handle OS commands as a fallback
                await handle_os_command(data, socket)

        except zmq.ZMQError as zmq_error:
            print(f"ZMQError: {zmq_error}")
        except json.JSONDecodeError as json_error:
            print(f"JSONError: {json_error}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            try:
                await socket.send_string(f"ERROR: {str(e)}")
            except zmq.ZMQError as zmq_error:
                print(f"Error sending error message: {zmq_error}")


if __name__ == "__main__":
    asyncio.run(backend_server())
