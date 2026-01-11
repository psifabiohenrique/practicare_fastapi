from enum import Enum


class Weekdays(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHERS = "Others"
