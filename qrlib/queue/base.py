"""
@rkp
"""
class QueueBase():
    """
    Not Implemented
    """
    def __init__(self,*args,**kwargs) -> None:
        for key,value in kwargs:
            setattr(self,key,value)

    def base_configs():

        return {
            "base_url":None,
            }