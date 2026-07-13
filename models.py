import datetime

class Resource:
    def __init__(self, resource_id: int, name: str, capacity: int, current_occupancy: int = 0):
        self.id = resource_id
        self.name = name
        self.capacity = capacity
        self.current_occupancy = current_occupancy

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "current_occupancy": self.current_occupancy,
            "available_slots": self.capacity - self.current_occupancy
        }


class Service:
    def __init__(self, service_id: int, resource_id: int, name: str, first_hour_rate: int, additional_hour_rate: int):
        self.id = service_id
        self.resource_id = resource_id
        self.name = name
        self.first_hour_rate = first_hour_rate
        self.additional_hour_rate = additional_hour_rate

    def to_dict(self):
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "name": self.name,
            "first_hour_rate": self.first_hour_rate,
            "additional_hour_rate": self.additional_hour_rate
        }


class Usage:
    def __init__(self, usage_id: int, resource_id: int, service_id: int, user_name: str,
                 start_time: datetime.datetime, end_time: datetime.datetime = None, status: str = "ACTIVE"):
        self.id = usage_id
        self.resource_id = resource_id
        self.service_id = service_id
        self.user_name = user_name
        self.start_time = start_time
        self.end_time = end_time
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "service_id": self.service_id,
            "user_name": self.user_name,
            "start_time": self.start_time.strftime("%Y-%m-%d %I:%M %p") if self.start_time else None,
            "end_time": self.end_time.strftime("%Y-%m-%d %I:%M %p") if self.end_time else None,
            "status": self.status
        }


class Bill:
    def __init__(self, bill_id: int, usage_id: int, user_name: str, resource_name: str,
                 start_time: datetime.datetime, end_time: datetime.datetime,
                 total_duration_minutes: int, rounded_hours: int, total_amount: int):
        self.id = bill_id
        self.usage_id = usage_id
        self.user_name = user_name
        self.resource_name = resource_name
        self.start_time = start_time
        self.end_time = end_time
        self.total_duration_minutes = total_duration_minutes
        self.rounded_hours = rounded_hours
        self.total_amount = total_amount

    def to_dict(self):
        return {
            "id": self.id,
            "usage_id": self.usage_id,
            "user_name": self.user_name,
            "resource_name": self.resource_name,
            "start_time": self.start_time.strftime("%Y-%m-%d %I:%M %p"),
            "end_time": self.end_time.strftime("%Y-%m-%d %I:%M %p"),
            "total_duration_minutes": self.total_duration_minutes,
            "rounded_hours": self.rounded_hours,
            "total_amount": self.total_amount
        }
