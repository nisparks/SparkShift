"""Checked two-joint kinematic preview; not a spring-force simulation."""

import bisect
import hashlib
import html
import json
import math
from pathlib import Path
import time
import traceback
import uuid

import adsk.core
import adsk.fusion


DATA = Path(__file__).with_name("cam_motion.json")
COMMAND_ID = "SparkShiftCamPlayback"
_handlers = []
_command = None
_busy = False
_managed_by_bridge = False
_last_error = None


def load_data():
    content = DATA.read_bytes()
    data = json.loads(content)
    if (data["schema"] != 1 or data["cam_range_deg"] != [0, 175]
            or data["samples"][0][0] != 0 or data["samples"][-1][0] != 175
            or any(a[0] >= b[0] for a, b in zip(data["samples"], data["samples"][1:]))):
        raise ValueError("The checked cam-contact playback data is invalid")
    return data, hashlib.sha256(content).hexdigest()


def validate(design):
    if design is None:
        raise RuntimeError("Open a compatible SparkShift cam-preview model")
    data, digest = load_data()
    root = design.rootComponent
    attribute = root.attributes.itemByName("SparkShiftMotion", "playback_data_sha256")
    if attribute is None or attribute.value != digest:
        raise RuntimeError("This model does not match the checked v15 playback data")
    if any(not t.isSuppressed for t in root.tangentRelationships):
        raise RuntimeError("Disable the diagnostic tangent relationship before curve playback")
    if design.isContactAnalysisEnabled:
        raise RuntimeError("The checked kinematic preview does not use contact-force analysis")
    for name in ("J_CAM", "J_C"):
        joint = root.joints.itemByName(name)
        if joint is None or joint.isLocked:
            raise RuntimeError("The required free native joint is unavailable: " + name)
    if (not root.joints.itemByName("J_SC").isSuppressed
            or not root.motionLinks.itemByName("CLAMPED_HOB_14_37").isSuppressed):
        raise RuntimeError("Use release-preview mode, not simultaneous feed simulation")
    frame = next(o for o in root.occurrences if o.name.startswith("01 "))
    if max(abs(a-b) for a, b in zip(
            frame.transform2.asArray(), data["fixed_frame_transform"])) > 1e-8:
        raise RuntimeError("The assembly datum moved; regenerate the checked playback data")
    for prefix, expected in data["held_input_transforms"].items():
        occurrence = next(o for o in root.occurrences if o.name.startswith(prefix+" "))
        if max(abs(a-b) for a, b in zip(occurrence.transform2.asArray(), expected)) > 1e-8:
            raise RuntimeError("The held feed input moved; regenerate the checked release data")
    return root, data


def arm_angle(data, cam):
    samples = data["samples"]
    index = bisect.bisect_left([row[0] for row in samples], cam)
    if index == 0:
        return samples[0][1]
    if index == len(samples):
        return samples[-1][1]
    a, b = samples[index-1:index+1]
    return a[1]+(b[1]-a[1])*(cam-a[0])/(b[0]-a[0])


def rotation(angle, centre):
    matrix = adsk.core.Matrix3D.create()
    if not matrix.setToRotation(
            math.radians(angle), adsk.core.Vector3D.create(0, 1, 0),
            adsk.core.Point3D.create(*(value/10 for value in centre))):
        raise RuntimeError("The checked native revolute transform could not be formed")
    return matrix


def compose(left, right):
    a, b = left.asArray(), right.asArray()
    matrix = adsk.core.Matrix3D.create()
    if not matrix.setWithArray([
            sum(a[row*4+k]*b[k*4+column] for k in range(4))
            for row in range(4) for column in range(4)]):
        raise RuntimeError("The native carrier transform could not be composed")
    return matrix


def current_cam(root):
    occurrence = next(o for o in root.occurrences if o.name.startswith("10 "))
    matrix = occurrence.transform2.asArray()
    angle = math.degrees(math.atan2(matrix[2], matrix[0]))
    if abs(angle) < 1e-9:
        return 0.
    if abs(angle-175) < 1e-9:
        return 175.
    return angle


def drive(app, target):
    if not math.isfinite(target) or not 0 <= target <= 175:
        raise ValueError("Choose a cam angle from 0 through 175 degrees")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root, data = validate(design)
    parents = {o.name[:2]: o for o in root.occurrences if o.name[:2].isdigit()}
    desired = arm_angle(data, target)
    hob_relative = -data["moving_hob_ratio"]*(data["held_left_compound_deg"]-desired)
    carrier = rotation(desired, data["arm_pivot_mm"])
    poses = {"10": rotation(target, data["cam_pivot_mm"]), "05": carrier,
             "07": compose(carrier, rotation(hob_relative, data["moving_hob_axis_mm"])),
             "09": carrier, "11": carrier}
    changed = False
    for prefix, pose in poses.items():
        if max(abs(a-b) for a, b in zip(
                parents[prefix].transform2.asArray(), pose.asArray())) > 1e-12:
            parents[prefix].transform2 = pose
            changed = True
    if abs(current_cam(root)-target) > 1e-6:
        raise RuntimeError("The real cam transform does not match its checked pose")
    world = parents["05"].transform2.asArray()
    if abs(math.degrees(math.atan2(world[2], world[0]))-desired) > 1e-6:
        raise RuntimeError("The real arm transform does not match its checked pose")
    return {"cam_deg": target, "arm_deg": desired,
            "pose_changed": changed, "native_joint_angle_field_not_used": True}


def play_cycle(app, command, slider, document):
    initial = slider.valueOne
    for angle in [*range(0, 176, 2), 175, *range(174, -1, -2)]:
        if not command.isValid or app.activeDocument.creationId != document:
            return
        drive(app, angle)
        slider.valueOne = angle
        app.activeViewport.refresh()
        adsk.doEvents()
        time.sleep(.5 if angle in (0, 175) else .035)
    if command.isValid and app.activeDocument.creationId == document:
        drive(app, initial)
        slider.valueOne = initial
        app.activeViewport.refresh()


def inspection_view(app):
    root, _ = validate(adsk.fusion.Design.cast(app.activeProduct))
    for occurrence in root.allOccurrences:
        for body in occurrence.bRepBodies:
            if (body.name in ("PRINT_000_outer_shell_of_extruder_1", "PRINT_arm_front_half")
                    or body.name.startswith(("OCT_RECEIVER_MAGNET_", "OCT_LOCATOR_PIN_"))):
                body.isLightBulbOn = False
    for occurrence in root.occurrences:
        if occurrence.name.startswith(("12 ", "13 ")):
            occurrence.isLightBulbOn = False
    root.isJointsFolderLightBulbOn = False
    camera = adsk.core.Camera.create()
    camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    camera.isSmoothTransition = False
    camera.isFitView = False
    camera.target = adsk.core.Point3D.create(-1.0242788275103756, 1.8, 2.772415577900977)
    camera.eye = adsk.core.Point3D.create(-1.0242788275103756, 104.230573803655,
                                         2.772415577900977)
    camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
    camera.viewExtents = 10.243057532998947
    app.activeViewport.camera = camera
    app.activeViewport.refresh()


class Changed(adsk.core.InputChangedEventHandler):
    def __init__(self, command, document):
        super().__init__()
        self.command = command
        self.document = document

    def notify(self, arguments):
        global _busy, _last_error
        if _busy or _last_error is not None or not self.command.isValid:
            return
        app = adsk.core.Application.get()
        if app.activeDocument.creationId != self.document:
            app.userInterface.messageBox("The playback document is no longer active.")
            return
        _busy = True
        try:
            inputs = self.command.commandInputs
            slider = inputs.itemById("cam_angle")
            if arguments.input.id == "cam_angle":
                result = drive(app, slider.valueOne)
                if result["pose_changed"]:
                    app.activeViewport.refresh()
            elif arguments.input.id == "play" and arguments.input.value:
                arguments.input.value = False
                play_cycle(app, self.command, slider, self.document)
        except (RuntimeError, ValueError, OSError):
            _last_error = traceback.format_exc()
            app.log("Cam playback stopped:\n"+_last_error)
            if self.command.isValid:
                self.command.commandInputs.itemById("notice").formattedText = (
                    "<b>Playback stopped</b><br>"+html.escape(_last_error).replace("\n", "<br>"))
                self.command.commandInputs.itemById("cam_angle").isEnabled = False
                self.command.commandInputs.itemById("play").isEnabled = False
        finally:
            _busy = False


class Destroyed(adsk.core.CommandEventHandler):
    def notify(self, arguments):
        global _command
        _command = None
        if not _managed_by_bridge:
            adsk.terminate()


class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, arguments):
        global _command
        app = adsk.core.Application.get()
        root, _ = validate(adsk.fusion.Design.cast(app.activeProduct))
        command = arguments.command
        _command = command
        command.isRepeatable = False
        command.okButtonText = "Done"
        slider = command.commandInputs.addFloatSliderCommandInput(
            "cam_angle", "Cam angle (deg)", "", 0., 175., False)
        slider.valueOne = current_cam(root)
        command.commandInputs.addBoolValueInput("play", "Play one open/close cycle",
                                               True, "", False)
        command.commandInputs.addTextBoxCommandInput(
            "notice", "", "Progressive cam-contact playback, not force simulation.<br>"
            "Full-open dwell: 170-175 deg. Nominal upper margin: 5 deg.", 3, True)
        changed = Changed(command, app.activeDocument.creationId)
        destroyed = Destroyed()
        command.inputChanged.add(changed)
        command.destroy.add(destroyed)
        _handlers.extend((changed, destroyed))


def run(context):
    global _managed_by_bridge, _last_error, COMMAND_ID
    app = adsk.core.Application.get()
    ui = app.userInterface
    if _command is not None and _command.isValid:
        if ui.activeCommand == COMMAND_ID and _last_error is None:
            app.log("The checked cam preview is already open")
            return
        raise RuntimeError("Close the previous cam preview before starting another")
    _last_error = None
    _managed_by_bridge = isinstance(context, dict) and context.get("managed_by_bridge", False)
    root, _ = validate(adsk.fusion.Design.cast(app.activeProduct))
    drive(app, current_cam(root))
    inspection_view(app)
    previous = ui.commandDefinitions.itemById(COMMAND_ID)
    if previous is not None and not previous.deleteMe():
        app.log("Fusion retained an inactive preview definition; using an isolated instance")
    COMMAND_ID = "SparkShiftCamPlayback_"+uuid.uuid4().hex
    definition = ui.commandDefinitions.addButtonDefinition(
        COMMAND_ID, "SparkShift progressive cam", "Checked 0-175 degree cam-contact preview")
    created = Created()
    definition.commandCreated.add(created)
    _handlers.append(created)
    definition.execute()
    if not _managed_by_bridge:
        adsk.autoTerminate(False)


def stop(context):
    app = adsk.core.Application.get()
    definition = app.userInterface.commandDefinitions.itemById(COMMAND_ID)
    if definition is not None:
        definition.deleteMe()
