## Architecture Overview

### App model

```{eval-rst}
.. uml:: uml/app_model.plantuml
```

### App runner activity diagram

```{eval-rst}
.. uml::

    title
      App Runner Activity Diagram
    end title

    start
    :workunit_ref]
    partition App Runner {
      :Retrieve workunit and app information;
      split
        :workunit_definition.yml]
      split again
      :app_definition.yml]
      note right
        These are maintained in a
        centralized repository.
      end note
      end split

      :Set workunit processing status;
      :""app-runner app dispatch"";
      note right
        This step is supposed to be deterministic!
        To allow distributing the tasks in the future.
      end note
      split
        :tasks.yml]
      split again
        :task1/inputs.yml
        task1/params.yml]
      split again
        :task2/inputs.yml
        task2/params.yml]
      end split
    ' Unclear
    '  :Precondition check;
      :""app-runner chunk process-all""]
    }

    note right
       The actual ordering will be decided here.
       tasks.yml declares task dependencies.
    end note
    fork
        :Stage inputs 1;
        partition App {
          :Run task 1;
          :outputs.yml]
        }
        :Register outputs;
    fork again
        :Stage inputs 2;
        partition App {
          :Run task 2;
          :outputs.yml]
        }
        :Register outputs;
    end fork

    :Set workunit available status;
    stop
```
