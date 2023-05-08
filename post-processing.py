'''
Post-Processing Volumes with Metadata in Autodesk VRED

1. Create a box that acts as a processing volume and apply a transparent material to it
2. Add a VRED-tag "postProcessingVolume" to the box
3. Create a metadata set, name it "PostProcessing_CarInterior" and add it to the box
4. Add the metadata key-values "camera:exposure" and "camera:saturation" to the metadata set
5. Run the script and move the camera inside the box. The cameras exposure and saturation will change

Author: Christopher Gebhardt
Email: cg@ideenkultivierung
License: MIT
Date: 2023-05-08
'''


class PostProcessingController(vrAEBase):
    '''
    The post processing controller utilizes VREDs vrAEBase class to hook into the 
    update loop. This way it is possible to check every frame if the camera is inside
    a post processing volume and change the cameras settings accordingly.
    '''

    def __init__(self):
        vrAEBase.__init__(self)
        self.camera = vrCameraService.getActiveCamera()

        # Initialize the post processing volumes and the mapping between the volumes and the post processing effects
        self.postProcessingVolumes = self.initializePostProcessingVolumes()
        self.postProcessingEffectMapping = self.initializePostProcessingEffectMapping()

        # Read the cameras default settings to be able to reset them
        self.originalCameraParameters = {
            "exposure": self.camera.getTonemapper().getExposure(),
            "saturation": self.camera.getColorCorrectionSaturation(),
        }

        # The target values are used to smoothly transition the cameras settings
        self.exposureTarget = self.originalCameraParameters["exposure"]
        self.saturationTarget = self.originalCameraParameters["saturation"]

        self.lastActiveProcessingVolume = None

        self.addLoop()
        self.setActive(True)

    def initializePostProcessingVolumes(self):
        '''
        Get a list of all post processing volumes defined in the scene
        '''
        objects = vrMetadataService.getObjectsWithTag("postProcessingVolume")
        return [vrdNode(o) for o in objects]

    def initializePostProcessingEffectMapping(self):
        '''
        Initialize a dictionary that maps volume names to its attached post processing effect
        '''
        metadataSets = vrMetadataService.getAllSets()
        postProcessingMetaDataSets = [
            s for s in metadataSets if s.getName().startswith("PostProcessing")]

        postProcessingEffectMapping = {}
        for postProcessingMetaDataSet in postProcessingMetaDataSets:
            nodes = [vrdNode(n)
                     for n in postProcessingMetaDataSet.getObjects()]
            for node in nodes:
                postProcessingEffectMapping[node.getName(
                )] = postProcessingMetaDataSet

        return postProcessingEffectMapping

    def loop(self):
        '''
        This loop runs every frame and checks if the camera is inside a post processing volume
        If a viewer enters a post processing volume, the cameras values are changed to the values
        defined in the post processing volumes metadata.

        If the viewer leaves a post processing volume, the cameras values are reset to the original values
        '''
        if self.isActive() == True:
            activeProcessingVolume = None

            # Check if camera is inside camera volumes
            for postProcessingVolume in self.postProcessingVolumes:
                isCameraInside = self.isCameraInsideBoundingBox(
                    self.camera, postProcessingVolume)

                if isCameraInside:
                    activeProcessingVolume = postProcessingVolume

            # Check if the active processing volume has changed. This means
            # that the camera has entered or left a post processing volume
            if self.lastActiveProcessingVolume != activeProcessingVolume:

                # If the camera has entered a post processing volume, set the post processing effects
                # Otherwise reset the post processing effects
                if activeProcessingVolume != None:
                    self.setPostProcessingEffects(activeProcessingVolume)
                else:
                    self.resetPostProcessingEffects()

            self.lastActiveProcessingVolume = activeProcessingVolume

        self.smoothCameraParameterUpdate()

    def isCameraInsideBoundingBox(self, camera, volume):
        """
        Check if the camera is inside a bounding box
        """
        cameraPosition = camera.getWorldTranslation()
        boundingBox = volume.getBoundingBox()
        min = boundingBox.getMin()
        max = boundingBox.getMax()

        isInsideX = min.x() < cameraPosition.x() < max.x()
        isInsideY = min.y() < cameraPosition.y() < max.y()
        isInsideZ = min.z() < cameraPosition.z() < max.z()

        return isInsideX and isInsideY and isInsideZ

    def setPostProcessingEffects(self, postProcessingVolume):
        """
        Set the cameras exposure and saturation based on the post processing volume
        """

        print("Camera entered post processing volume: " +
              postProcessingVolume.getName())

        if postProcessingVolume.getName() in self.postProcessingEffectMapping:
            effect = self.postProcessingEffectMapping[postProcessingVolume.getName(
            )]
            exposure = effect.getValue("camera:exposure")
            saturation = effect.getValue("camera:saturation")

            self.exposureTarget = exposure
            self.saturationTarget = saturation

    def resetPostProcessingEffects(self):
        '''
        Reset the cameras exposure and saturation to the original values
        '''
        print("Camera left post processing volume")

        self.exposureTarget = self.originalCameraParameters["exposure"]
        self.saturationTarget = self.originalCameraParameters["saturation"]

    def smoothCameraParameterUpdate(self):
        '''
        Smoothly update the cameras exposure and saturation to the target values
        '''
        currentExposure = self.camera.getTonemapper().getExposure()
        currentSaturation = self.camera.getColorCorrectionSaturation()

        diffExposure = abs(self.exposureTarget - currentExposure)
        diffSaturation = abs(self.saturationTarget - currentSaturation)

        if diffExposure > 0.1:
            self.camera.getTonemapper().setExposure(
                currentExposure + (self.exposureTarget - currentExposure) * 0.1)

        if diffSaturation > 0.1:
            self.camera.setColorCorrectionSaturation(
                currentSaturation + (self.saturationTarget - currentSaturation) * 0.1)


# Initialize the controller
postProcessingController = PostProcessingController()
