# import zmq
# import zmq.asyncio
# import asyncio
#
# async def proxy(frontend, backend):
#     while True:
#         try:
#             # Wait for the frontend to send a message (client)
#             message = await frontend.recv_multipart()
#             print(f"Received message from client: {message}")
#
#             # Forward the message to the backend (worker)
#             await backend.send_multipart(message)
#             print(f"Forwarded message to worker: {message}")
#
#             # Wait for the backend to send a response (worker)
#             response = await backend.recv_multipart()
#             print(f"Received response from worker: {response}")
#
#             # Forward the response back to the frontend (client)
#             await frontend.send_multipart(response)
#             print(f"Forwarded response to client: {response}")
#
#         except zmq.ZMQError as e:
#             print(f"Broker error: {e}")
#             break
#
# async def broker():
#     context = zmq.asyncio.Context()
#     frontend = context.socket(zmq.ROUTER)  # For clients
#     backend = context.socket(zmq.DEALER)  # For workers
#
#     frontend.bind("tcp://*:5555")
#     backend.bind("tcp://*:5556")
#
#     print("Broker is running...")
#
#     try:
#         await proxy(frontend, backend)  # Manually forward messages
#     except zmq.ZMQError as e:
#         print(f"Broker error: {e}")
#     finally:
#         frontend.close()
#         backend.close()
#         context.term()
#
# if __name__ == "__main__":
#     asyncio.run(broker())
