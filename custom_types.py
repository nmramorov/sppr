
class AbstractFeature:
    def __init__(self, features: str):
        features_list = features.split(' ')
        self.length = len(features_list)

        for index, feature in enumerate(features_list):
            setattr(self, feature, index)

    def __len__(self):
        return self.length


class FunctionalFeature(AbstractFeature):
    def __init__(self):
        functional_features = "start breathlessness weight_changed heart_failure_complaints heart_rhythm_type " \
                              "position_in_bed swollen_cervical_veins wheezing_in_lungs liver_state " \
                              "edema systolic_pressure"
        super().__init__(functional_features)

    def __len__(self):
        return self.length
