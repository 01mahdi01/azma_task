import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ValidationError
from channels.exceptions import StopConsumer
from jsonschema import validate, ValidationError as JSONValidationError
import zmq.asyncio

from .validators import MY_JSON_FIELD_SCHEMA


class CommandConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling commands sent by clients.

    This consumer processes JSON commands, validates them, and performs specific actions
    based on the command type. Supported command types include:
    - OS-related commands
    - Math evaluations
    - Stopping specific backend processes

    The consumer uses ZeroMQ (ZMQ) for communicating with backend systems.
    """

    async def connect(self):
        """
        Handle WebSocket connection establishment.

        Initializes the ZeroMQ context and socket, subscribes to the channel layer group,
        and accepts the WebSocket connection.
        """
        self.room_name = "commands"
        self.room_group_name = f"command_{self.room_name}"

        if not self.channel_layer:
            print("Channel layer is not available.")
            await self.close()
            return

        try:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Initialize ZeroMQ context and socket
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.PAIR)
            self.socket.connect("tcp://localhost:5556")

        except Exception as e:
            print(f"Error during WebSocket connection: {e}")
            await self.close()
            raise StopConsumer()

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Closes the ZeroMQ socket and context, and removes the WebSocket from the channel group.
        """
        if hasattr(self, "socket"):
            self.socket.close()
            self.context.term()

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Handle messages received from the WebSocket.

        Parses the JSON message, validates it against a schema, and dispatches it to the appropriate handler.
        """
        try:
            command = json.loads(text_data)
            validate(instance=command, schema=MY_JSON_FIELD_SCHEMA)

            # Map command types to their respective handler methods
            command_handlers = {
                "os": self.stream_command,
                "math": self.handle_math_command,
                "stop_process": self.stop_process_command,
            }

            # Extract command fields
            command_type = command["command_type"]
            body = command["body"]
            parameters = command.get("parameters", [])

            # Dispatch the command to the corresponding handler
            handler = command_handlers.get(command_type)
            if handler:
                await handler(body, parameters)
            else:
                await self.send(json.dumps({"error": "Invalid command type."}))

        except JSONValidationError as ve:
            await self.send(json.dumps({"error": f"JSON validation error: {ve.message}"}))
        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON format."}))
        except Exception as e:
            await self.send(json.dumps({"error": f"An error occurred: {str(e)}"}))

    async def stream_command(self, body, parameters):
        """
        Handle OS commands by streaming responses from the backend system.
        """
        try:
            command_to_send = json.dumps({"command": body, "parameters": parameters})
            self.socket.send_string(command_to_send)
            print(f"Sent command: {command_to_send}")

            while True:
                try:
                    events = await self.socket.poll(timeout=1000)
                    if events:
                        output = await self.socket.recv_string()
                        print(f"Received output: {output}")

                        if output == "STREAM_END":
                            break

                        await self.send(json.dumps({"output": output}))
                    else:
                        break
                except zmq.Again:
                    await asyncio.sleep(0.9)
                except Exception as e:
                    await self.send(json.dumps({"error": f"Error streaming command: {str(e)}"}))
                    break

        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def handle_math_command(self, expression, parameters):
        """
        Evaluate and send the result of a mathematical expression.
        """
        try:
            full_expression = expression + " " + " ".join(parameters)
            result = eval(full_expression)
            await self.send(json.dumps({"result": result}))
        except Exception as e:
            await self.send(json.dumps({"error": f"Math evaluation error: {str(e)}"}))

    async def stop_process_command(self, body, parameters):
        """
        Send a stop command to terminate a specific backend process.
        """
        try:
            process_details = {param.split(":")[0]: param.split(":")[1] for param in parameters}
            command_id = process_details.get("command_id")

            if not command_id:
                raise ValueError("No valid command_id provided.")

            stop_message = json.dumps({"command": "STOP", "command_id": command_id})
            self.socket.send_string(stop_message)
            print(f"Sent stop command with command_id: {command_id}")

            while True:
                try:
                    events = await self.socket.poll(timeout=100)
                    if events:
                        output = self.socket.recv_string()
                        print(f"Received output: {output}")

                        response = json.loads(output)
                        if response.get("status") == "success":
                            await self.send(json.dumps({"status": "success", "message": response["message"]}))
                            break
                        elif response.get("status") == "error":
                            await self.send(json.dumps({"error": response["message"]}))
                            break
                except zmq.Again:
                    await asyncio.sleep(0.1)
                except Exception as e:
                    await self.send(json.dumps({"error": f"Error stopping process: {str(e)}"}))
                    break

        except Exception as e:
            await self.send(json.dumps({"error": f"Failed to stop process: {str(e)}"}))
