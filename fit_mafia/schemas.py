from marshmallow import Schema, fields

class MemberSchema(Schema):
    """Schema for member data to ensure consistent API responses."""
    id = fields.Int(dump_only=True)
    mobile_number = fields.Str(required=True)
    first_name = fields.Str()
    last_name = fields.Str()
    password = fields.Str()
    email = fields.Email()
    dob = fields.Str()
    gender = fields.Str()
    address = fields.Str()
    joining_date = fields.Str()
    status = fields.Str(dump_only=True)
    subscription = fields.Str()
    subscription_start_date = fields.Str()
    subscription_end_date = fields.Str()
    height = fields.Float()
    weight = fields.Float()
    bmi = fields.Float()
    photo = fields.Str()


class LoginRequestSchema(Schema):
    username = fields.Str(required=True, description="User's login name")
    password = fields.Str(required=True, description="User's password")