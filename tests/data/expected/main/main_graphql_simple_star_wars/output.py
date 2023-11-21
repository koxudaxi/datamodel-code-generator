# generated by datamodel-codegen:
#   filename:  simple-star-wars.graphql
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import List, Literal, Optional, TypeAlias

from pydantic import BaseModel, Field

# The `Boolean` scalar type represents `true` or `false`.
Boolean: TypeAlias = bool


# The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.
ID: TypeAlias = str


# The `Int` scalar type represents non-fractional signed whole numeric values. Int can represent values between -(2^31) and 2^31 - 1.
Int: TypeAlias = int


# The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
String: TypeAlias = str


class Film(BaseModel):
    characters: List[Person]
    characters_ids: List[ID]
    director: String
    episode_id: Int
    id: ID
    opening_crawl: String
    planets: List[Planet]
    planets_ids: List[ID]
    producer: Optional[String] = None
    release_date: String
    species: List[Species]
    species_ids: List[ID]
    starships: List[Starship]
    starships_ids: List[ID]
    title: String
    vehicles: List[Vehicle]
    vehicles_ids: List[ID]
    typename__: Optional[Literal['Film']] = Field('Film', alias='__typename')


class Person(BaseModel):
    birth_year: Optional[String] = None
    eye_color: Optional[String] = None
    films: List[Film]
    films_ids: List[ID]
    gender: Optional[String] = None
    hair_color: Optional[String] = None
    height: Optional[Int] = None
    homeworld: Optional[Planet] = None
    homeworld_id: Optional[ID] = None
    id: ID
    mass: Optional[Int] = None
    name: String
    skin_color: Optional[String] = None
    species: List[Species]
    species_ids: List[ID]
    starships: List[Starship]
    starships_ids: List[ID]
    vehicles: List[Vehicle]
    vehicles_ids: List[ID]
    typename__: Optional[Literal['Person']] = Field('Person', alias='__typename')


class Planet(BaseModel):
    climate: Optional[String] = None
    diameter: Optional[String] = None
    films: List[Film]
    films_ids: List[ID]
    gravity: Optional[String] = None
    id: ID
    name: String
    orbital_period: Optional[String] = None
    population: Optional[String] = None
    residents: List[Person]
    residents_ids: List[ID]
    rotation_period: Optional[String] = None
    surface_water: Optional[String] = None
    terrain: Optional[String] = None
    typename__: Optional[Literal['Planet']] = Field('Planet', alias='__typename')


class Species(BaseModel):
    average_height: Optional[String] = None
    average_lifespan: Optional[String] = None
    classification: Optional[String] = None
    designation: Optional[String] = None
    eye_colors: Optional[String] = None
    films: List[Film]
    films_ids: List[ID]
    hair_colors: Optional[String] = None
    id: ID
    language: Optional[String] = None
    name: String
    people: List[Person]
    people_ids: List[ID]
    skin_colors: Optional[String] = None
    typename__: Optional[Literal['Species']] = Field('Species', alias='__typename')


class Starship(BaseModel):
    MGLT: Optional[String] = None
    cargo_capacity: Optional[String] = None
    consumables: Optional[String] = None
    cost_in_credits: Optional[String] = None
    crew: Optional[String] = None
    films: List[Film]
    films_ids: List[ID]
    hyperdrive_rating: Optional[String] = None
    id: ID
    length: Optional[String] = None
    manufacturer: Optional[String] = None
    max_atmosphering_speed: Optional[String] = None
    model: Optional[String] = None
    name: String
    passengers: Optional[String] = None
    pilots: List[Person]
    pilots_ids: List[ID]
    starship_class: Optional[String] = None
    typename__: Optional[Literal['Starship']] = Field('Starship', alias='__typename')


class Vehicle(BaseModel):
    cargo_capacity: Optional[String] = None
    consumables: Optional[String] = None
    cost_in_credits: Optional[String] = None
    crew: Optional[String] = None
    films: List[Film]
    films_ids: List[ID]
    id: ID
    length: Optional[String] = None
    manufacturer: Optional[String] = None
    max_atmosphering_speed: Optional[String] = None
    model: Optional[String] = None
    name: String
    passengers: Optional[String] = None
    pilots: List[Person]
    pilots_ids: List[ID]
    vehicle_class: Optional[String] = None
    typename__: Optional[Literal['Vehicle']] = Field('Vehicle', alias='__typename')
