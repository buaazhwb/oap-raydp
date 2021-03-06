#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys

import databricks.koalas as ks
import pytest
import torch

import raydp.spark.context as context
from raydp.spark.torch.estimator import TorchEstimator
from raydp.spark.utils import random_split


def test_torch_estimator(ray_cluster):
    # ---------------- data process with koalas ------------
    app_name = "A simple example for spark on ray"
    context.init_spark(app_name, 2, 1, "500MB")

    # calculate z = 3 * x + 4 * y + 5
    df: ks.DataFrame = ks.range(0, 100000)
    df["x"] = df["id"] + 100
    df["y"] = df["id"] + 1000
    df["z"] = df["x"] * 3 + df["y"] * 4 + 5
    df = df.astype("float")

    train_df, test_df = random_split(df, [0.7, 0.3])

    # ---------------- ray sgd -------------------------
    # create the model
    model = torch.nn.Sequential(torch.nn.Linear(2, 1))
    # create the optimizer
    optimizer = torch.optim.Adam(model.parameters())
    # create the loss
    loss = torch.nn.MSELoss()
    # create lr_scheduler

    def lr_scheduler_creator(optimizer, config):
        return torch.optim.lr_scheduler.MultiStepLR(
            optimizer, milestones=[150, 250, 350], gamma=0.1)

    # create the estimator
    estimator = TorchEstimator(num_workers=2,
                               model=model,
                               optimizer=optimizer,
                               loss=loss,
                               lr_scheduler_creator=lr_scheduler_creator,
                               feature_columns=["x", "y"],
                               label_column="z",
                               batch_size=1000,
                               num_epochs=2)

    # train the model
    estimator.fit(train_df)
    # evaluate the model
    estimator.evaluate(test_df)

    # get the model
    model = estimator.get_model()
    print(list(model.parameters()))

    estimator.shutdown()
    context.stop_spark()


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))