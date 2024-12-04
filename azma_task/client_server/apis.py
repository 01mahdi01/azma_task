from django.http import StreamingHttpResponse
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import zmq


class CommandAPIView(APIView):
    class InputCommandSerializer(serializers.Serializer):
        command = serializers.JSONField()

    def validate(self, data):
        data.get("command")

    class OutputCommandSerializer(serializers.Serializer):
        result = serializers.JSONField()


    def post(self, request):
        serializer = self.InputCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        command = request.data.get("command")

        if not command:
            return Response({"error": "Command not provided."}, status=status.HTTP_400_BAD_REQUEST)

        command_type = command.get("type")
        if command_type is "os":
            try:
                def stream_command():
                    context = zmq.Context()
                    socket = context.socket(zmq.REQ)
                    socket.connect("tcp://localhost:5556")
                    socket.send_string(command)  # Send the command to the backend

                    while True:
                        output = socket.recv_string()
                        if output == "STREAM_END":
                            break
                        yield output + "\n"  # Stream output line by line
                    socket.close()

                return StreamingHttpResponse(stream_command(), content_type="text/plain")
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        elif command_type is "math":
            pass
