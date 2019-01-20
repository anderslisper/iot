from device_config import DeviceConfig
import json
import iothub_client
from iothub_client import IoTHubClient, IoTHubMessage, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult, IoTHubError

# choose HTTP, AMQP, AMQP_WS or MQTT as transport protocol
PROTOCOL = IoTHubTransportProvider.MQTT

TWIN_CONTEXT = 0
SEND_REPORTED_STATE_CONTEXT = 0

azure_singelton = None

# Local callbacks from iot_client
def device_twin_callback(update_state, payload, user_context):
    azure_singelton.device_twin_callback(update_state, payload, user_context)
    
def send_confirmation_callback(message, result, user_context):
    azure_singelton.send_confirmation_callback(message, result, user_context)

def send_reported_state_callback(status_code, user_context):
    azure_singelton.send_reported_state_callback(status_code, user_context)

class Azure:
    def __init__(self, application, device_config):
        global azure_singelton
        if azure_singelton is None:
            azure_singelton = self
        else:
            raise Exception("AZURE: AzureIot instance already created")

        with open('azure.json') as f:
            self.config = json.load(f)

        if self.config['connection_string'].find(device_config.deviceid) == -1:
            raise Exception("Azure connection string does not match configured device id")
            
        self.application = application
        self.hubClient   = IoTHubClient(self.config['connection_string'], PROTOCOL)
        if self.hubClient.protocol == IoTHubTransportProvider.MQTT or self.hubClient.protocol == IoTHubTransportProvider.MQTT_WS:
            self.hubClient.set_device_twin_callback(
                device_twin_callback, TWIN_CONTEXT)

    # Report current state to cloud
    def update_reported_state(self, reported):
        try:
            # Report new state to HUB
            reported_state = json.dumps(reported)
            self.hubClient.send_reported_state(reported_state, 
                                               len(reported_state), 
                                               send_reported_state_callback, 
                                               SEND_REPORTED_STATE_CONTEXT)
            return True
        except IoTHubError as iothub_error:
            print ( "AZURE: Unexpected error from IoTHub when reporting state: %s" % iothub_error )
        return False
        
    # Post telemetry to cloud
    def post_telemetry(self, telemetry):
        try:
            message = IoTHubMessage(json.dumps(telemetry))
            self.hubClient.send_event_async(message, send_confirmation_callback, None)
            return True
        except IoTHubError as iothub_error:
            print ( "AZURE: Unexpected error from IoTHub when posting telemetry: %s" % iothub_error )
        return False
    
    # Keep cloud connection open (not needed for azure)
    def kick(self):
        pass
        
    # Local callbacks from iot_client
    def device_twin_callback(self, update_state, payload, user_context):
        print ( "AZURE: Twin callback called with updateStatus: '%s'" % update_state )
        payload_json = json.loads(payload)
        if update_state == iothub_client.iothub_client.IoTHubTwinUpdateState.COMPLETE:
            desired_state = payload_json["desired"].copy()
        else:
            desired_state = payload_json.copy()
        self.application.device_twin_update(desired_state)

    def send_confirmation_callback(self, message, result, user_context):
        print ( "AZURE: IoT Hub responded to message with status: %s" % (result) )

    def send_reported_state_callback(self, status_code, user_context):
        print ( "AZURE: Confirmation for reported state called with status_code: %d" % status_code )

if __name__ == '__main__':
    pass