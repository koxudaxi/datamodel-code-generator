class ModelA(BaseModel):
    firstName: Optional[str] = None
    modelB: Optional[file_b.ModelB] = None


class ModelB(BaseModel):
    metadata: str


class ModelC(BaseModel):
    firstName: Optional[str] = None
    modelB: Optional[file_b.ModelB] = None


class ModelD(BaseModel):
    firstName: Optional[str] = None
    modelA: Optional[file_a.ModelA] = None