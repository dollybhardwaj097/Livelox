import boto3
import os
import sys


def get_asg_instances(asg_name):
    """
    Retrieve the instances associated with the given ASG name.
    """
    client = boto3.client('autoscaling')
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])

    if 'AutoScalingGroups' in response and response['AutoScalingGroups']:
        asg = response['AutoScalingGroups'][0]
        if 'Instances' in asg:
            return asg['Instances']

    return []


def verify_testcase_a():
    """
    Verify Testcase A:
    1. ASG desired count should be the same as running instances count.
    2. If more than 1 instance running, they should be distributed across availability zones.
    3. Verify SecurityGroup, ImageID, and VPCID are the same for all running instances.
    4. Find the uptime of instances and get the longest running instance.
    """
    instances = get_asg_instances(asg_name)

    # Check if desired count matches the running instances count
    asg_desired_count = len(instances)
    asg_running_count = sum(1 for instance in instances if instance['LifecycleState'] == 'InService')
    if asg_desired_count != asg_running_count:
        print("Testcase A - Failed: ASG desired running count does not match the running instances count.")
        return

    # Check if instances are distributed across availability zones
    availability_zones = set(instance['AvailabilityZone'] for instance in instances)
    if len(availability_zones) < 2:
        print("Testcase A - Failed: Instances are not distributed across multiple availability zones.")
        return

    # Verify SecurityGroup, ImageID, and VPCID are the same for all instances
    security_group = instances[0]['SecurityGroups'][0]['GroupId']
    image_id = instances[0]['ImageId']
    vpc_id = instances[0]['VpcId']
    for instance in instances:
        if instance['SecurityGroups'][0]['GroupId'] != security_group or instance['ImageId'] != image_id or instance['VpcId'] != vpc_id:
            print("Testcase A - Failed: SecurityGroup, ImageID, or VPCID differs among instances.")
            return

    # Calculate uptime of instances and find the longest running instance
    current_time = datetime.now()
    longest_uptime = timedelta()
    longest_running_instance = None
    for instance in instances:
        launch_time = instance['LaunchTime']
        uptime = current_time - launch_time
        if uptime > longest_uptime:
            longest_uptime = uptime
            longest_running_instance = instance

    print("Testcase A - Passed")
    print("Longest running instance ID:", longest_running_instance['InstanceId'])
    print("Longest running instance uptime:", longest_uptime)


def verify_testcase_b():
    """
    Verify Testcase B:
    1. Find the scheduled actions of the given ASG and calculate the elapsed time from the current time.
    2. Calculate the total number of instances launched and terminated on the current day for the given ASG.
    """
    client = boto3.client('autoscaling')

    # Retrieve scheduled actions
    response = client.describe_scheduled_actions(AutoScalingGroupName=asg_name)
    scheduled_actions = response['ScheduledUpdateGroupActions']

    if not scheduled_actions:
        print("No scheduled actions found for the ASG.")
    else:
        current_time = datetime.now()
        next_action = min(scheduled_actions, key=lambda x: x['StartTime'])
        start_time = next_action['StartTime']
        elapsed_time = start_time - current_time
        elapsed_hms = str(elapsed_time).split('.')[0]  # Format elapsed time as hh:mm:ss
        print("Next scheduled action start time:", start_time)
        print("Elapsed time from current time:", elapsed_hms)

    # Calculate launched and terminated instances count for the current day
    start_of_day = datetime.combine(datetime.today(), datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)

    response = client.describe_scaling_activities(AutoScalingGroupName=asg_name, StartTime=start_of_day, EndTime=end_of_day)
    activities = response['Activities']

    launched_count = sum(1 for activity in activities if activity['StatusCode'] == 'Successful' and activity['Description'].startswith('Launching a new EC2 instance'))

    terminated_count = sum(1 for activity in activities if activity['StatusCode'] == 'Successful' and activity['Description'].startswith('Terminating EC2 instance'))

    print("Launched instances count today:", launched_count)
    print("Terminated instances count today:", terminated_count)


def main():
    verify_testcase_a()
    print()
    verify_testcase_b()


if __name__ == '__main__':
    aws_access_key_id = os.environ['aws_access_key_id']
    aws_secret_access_key = os.environ['aws_secret_access_key']

    main()
